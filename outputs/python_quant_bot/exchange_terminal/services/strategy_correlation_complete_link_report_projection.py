"""Redacted public projection for verified report-17 complete-link evidence."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_complete_link_report_consumer import (
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_complete_link_report_extension,
)


PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-complete-link-report-public-summary-v1"
)
PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-complete-link-report-public-summary-verification-v1"
)
STATIC_FINGERPRINT = "20260822-complete-link-report-public-summary-1"

_PERMISSION = {
    "status": "RESEARCH_ONLY",
    "descriptive_only": True,
    "profitability_claim_allowed": False,
    "parameter_selection_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
}
_REDACTION = {
    "source_hashes_exposed": False,
    "strategy_identity_exposed": False,
    "variant_identity_exposed": False,
    "lane_identity_exposed": False,
    "cluster_identities_exposed": False,
    "symbol_identities_exposed": False,
    "correlation_matrix_exposed": False,
    "selection_cells_exposed": False,
    "raw_gate_exposed": False,
    "decision_blockers_exposed": False,
}


def _summary(decision: str | None) -> dict[str, Any]:
    observed = decision in {"PASS", "BLOCK"}
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "status": "OBSERVED" if observed else "UNKNOWN",
            "consumer_verification_status": "PASS" if observed else "UNKNOWN",
            "extension_schema_version": EXTENSION_SCHEMA_VERSION if observed else None,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION if observed else None,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION if observed else None,
            "target_protocol_schema_version": (
                TARGET_PROTOCOL_SCHEMA_VERSION if observed else None
            ),
        },
        "gap": {
            "status": (
                "FORMAL_REGISTRY_AND_WRITER_PENDING"
                if decision == "PASS"
                else "COMPLETE_LINK_DECISION_BLOCK"
                if decision == "BLOCK"
                else "SOURCE_INVALID"
            ),
            "decision": decision if observed else None,
            "formal_registry_status": "NOT_BOUND" if observed else "UNKNOWN",
            "writer_status": "NOT_IMPLEMENTED" if observed else "UNKNOWN",
            "current_activation_status": "NOT_ACTIVATED",
        },
        "maturity": {
            "status": (
                "CONSUMER_EVIDENCE_PASS"
                if decision == "PASS"
                else "CONSUMER_EVIDENCE_BLOCK"
                if decision == "BLOCK"
                else "UNKNOWN"
            ),
            "consumer_only": True,
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
        },
        "permission": dict(_PERMISSION),
        "redaction": dict(_REDACTION),
    }


def build_strategy_correlation_complete_link_report_public_summary(
    source_extension: Any,
    *,
    expected_base_report_hash: Any,
) -> dict[str, Any]:
    """Project only the verified aggregate decision from a report-17 extension."""

    try:
        verification = verify_strategy_correlation_complete_link_report_extension(
            source_extension,
            expected_base_report_hash=expected_base_report_hash,
        )
    except (TypeError, ValueError):
        return _summary(None)
    decision = verification.get("decision")
    if verification.get("status") != "PASS" or decision not in {"PASS", "BLOCK"}:
        return _summary(None)
    return _summary(str(decision))


def verify_strategy_correlation_complete_link_report_public_summary(
    document: Any,
    *,
    source_extension: Any,
    expected_base_report_hash: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_complete_link_report_public_summary(
        source_extension,
        expected_base_report_hash=expected_base_report_hash,
    )
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("complete_link_report_public_summary_invalid")
    else:
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
        if not strict_json_contract_equal(document, expected):
            blockers.append("complete_link_report_public_summary_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": list(dict.fromkeys(blockers)),
        "projection_status": (
            expected["maturity"]["status"] if status == "PASS" else "UNKNOWN"
        ),
        "decision": expected["gap"]["decision"] if status == "PASS" else None,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "PUBLIC_SUMMARY_SCHEMA_VERSION",
    "PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_complete_link_report_public_summary",
    "verify_strategy_correlation_complete_link_report_public_summary",
]
