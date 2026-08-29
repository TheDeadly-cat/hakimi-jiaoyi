"""Redacted public projection for preregistered correlation strata."""

from __future__ import annotations

from typing import Any

try:
    from services.strategy_correlation_preregistered_strata import (
        GATE_SCHEMA,
        REGISTRATION_SCHEMA,
        verify_strategy_correlation_strata_gate,
        verify_strategy_correlation_strata_preregistration,
    )
    from services.strict_canonical_json_hash import strict_json_contract_equal
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_preregistered_strata import (
        GATE_SCHEMA,
        REGISTRATION_SCHEMA,
        verify_strategy_correlation_strata_gate,
        verify_strategy_correlation_strata_preregistration,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-preregistered-strata-public-summary-v1"
)
STATIC_FINGERPRINT = "20260821-preregistered-strata-independence-ledger-1"


def _permission() -> dict[str, Any]:
    return {
        "status": "RESEARCH_ONLY",
        "descriptive_only": True,
        "profitability_claim_allowed": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _redaction() -> dict[str, bool]:
    return {
        "symbol_identities_exposed": False,
        "cluster_identities_exposed": False,
        "stratum_identities_exposed": False,
        "artifact_hashes_exposed": False,
        "raw_correlations_exposed": False,
        "selection_rankings_exposed": False,
    }


def _unknown_summary() -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "status": "UNKNOWN",
            "registration_schema": None,
            "gate_schema": None,
            "gate_evidence_status": "UNKNOWN",
            "cluster_count": None,
            "dimension_count": None,
            "stratum_count": None,
        },
        "gap": {
            "status": "UNKNOWN",
            "passing_dimension_count": None,
            "blocked_dimension_count": None,
        },
        "maturity": {
            "status": "UNKNOWN",
            "formal_registry": "UNKNOWN",
            "report_schema_integration": "UNKNOWN",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
        },
        "policy": {
            "maximum_votes_per_stratum": None,
            "minimum_independent_strata": None,
            "required_strata_fraction": None,
        },
        "permission": _permission(),
        "redaction": _redaction(),
    }


def build_strategy_correlation_strata_public_summary(
    source_registration: Any,
    *,
    source_preregistration: Any,
    source_gate: Any = None,
    complete_link_gate: Any = None,
) -> dict[str, Any]:
    try:
        registration_verification = (
            verify_strategy_correlation_strata_preregistration(
                source_registration,
                source_preregistration=source_preregistration,
            )
        )
        if registration_verification.get("status") != "PASS":
            return _unknown_summary()
        if type(source_registration) is not dict:
            return _unknown_summary()
        dimensions = source_registration.get("dimensions")
        cluster_ids = source_registration.get("cluster_ids")
        if type(dimensions) is not list or type(cluster_ids) is not list:
            return _unknown_summary()
        gate_supplied = source_gate is not None or complete_link_gate is not None
        if gate_supplied and (source_gate is None or complete_link_gate is None):
            return _unknown_summary()

        gap_status = "GATE_EVIDENCE_NOT_SUPPLIED"
        gate_evidence_status = "NOT_SUPPLIED"
        gate_schema = None
        passing_dimension_count = None
        blocked_dimension_count = None
        if gate_supplied:
            gate_verification = verify_strategy_correlation_strata_gate(
                source_gate,
                registration=source_registration,
                complete_link_gate=complete_link_gate,
                source_preregistration=source_preregistration,
            )
            if gate_verification.get("status") != "PASS":
                return _unknown_summary()
            if type(source_gate) is not dict:
                return _unknown_summary()
            dimension_results = source_gate.get("dimension_results")
            if type(dimension_results) is not list:
                return _unknown_summary()
            passing_dimension_count = sum(
                result.get("status") == "PASS"
                for result in dimension_results
                if type(result) is dict
            )
            blocked_dimension_count = sum(
                result.get("status") == "BLOCK"
                for result in dimension_results
                if type(result) is dict
            )
            if passing_dimension_count + blocked_dimension_count != len(
                dimension_results
            ):
                return _unknown_summary()
            gate_evidence_status = "OBSERVED"
            gate_schema = GATE_SCHEMA
            if source_gate.get("first_blocking_tier") == "BASE_COMPLETE_LINK":
                gap_status = "BASE_COMPLETE_LINK_BLOCK_OBSERVED"
            elif blocked_dimension_count:
                gap_status = "PARENT_STRATUM_CONCENTRATION_OBSERVED"
            elif source_gate.get("status") == "PASS":
                gap_status = "INDEPENDENCE_REQUIREMENTS_OBSERVED"
            else:
                return _unknown_summary()

        stratum_count = sum(
            len(dimension.get("strata", []))
            for dimension in dimensions
            if type(dimension) is dict
        )
        if len(dimensions) != sum(
            type(dimension) is dict for dimension in dimensions
        ):
            return _unknown_summary()
        return {
            "schema_version": PUBLIC_SUMMARY_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source": {
                "status": "OBSERVED",
                "registration_schema": REGISTRATION_SCHEMA,
                "gate_schema": gate_schema,
                "gate_evidence_status": gate_evidence_status,
                "cluster_count": len(cluster_ids),
                "dimension_count": len(dimensions),
                "stratum_count": stratum_count,
            },
            "gap": {
                "status": gap_status,
                "passing_dimension_count": passing_dimension_count,
                "blocked_dimension_count": blocked_dimension_count,
            },
            "maturity": {
                "status": "CONSUMER_ONLY",
                "formal_registry": "PENDING",
                "report_schema_integration": "PENDING",
                "writer": "NOT_IMPLEMENTED",
                "current": "NOT_ACTIVATED",
            },
            "policy": {
                "maximum_votes_per_stratum": source_registration[
                    "maximum_votes_per_stratum"
                ],
                "minimum_independent_strata": source_registration[
                    "minimum_independent_strata"
                ],
                "required_strata_fraction": source_registration[
                    "required_strata_fraction"
                ],
            },
            "permission": _permission(),
            "redaction": _redaction(),
        }
    except (MemoryError, RecursionError):
        raise
    except (KeyError, TypeError, ValueError):
        return _unknown_summary()


def verify_strategy_correlation_strata_public_summary(
    document: Any,
    *,
    source_registration: Any,
    source_preregistration: Any,
    source_gate: Any = None,
    complete_link_gate: Any = None,
) -> dict[str, Any]:
    expected = build_strategy_correlation_strata_public_summary(
        source_registration,
        source_preregistration=source_preregistration,
        source_gate=source_gate,
        complete_link_gate=complete_link_gate,
    )
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("strata_public_summary_contract_invalid")
    elif not strict_json_contract_equal(document, expected):
        blockers.append("strata_public_summary_exact_rebuild_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
    }
