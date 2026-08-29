"""Redacted public projection for verified report18 strata evidence."""

from __future__ import annotations

from typing import Any

try:
    from services.strategy_correlation_strata_report_consumer import (
        BASE_PROTOCOL_SCHEMA_VERSION,
        BASE_REPORT_SCHEMA_VERSION,
        EXTENSION_SCHEMA_VERSION,
        TARGET_PROTOCOL_SCHEMA_VERSION,
        TARGET_REPORT_SCHEMA_VERSION,
        verify_strategy_correlation_strata_report_extension,
    )
    from services.strict_canonical_json_hash import strict_json_contract_equal
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_strata_report_consumer import (
        BASE_PROTOCOL_SCHEMA_VERSION,
        BASE_REPORT_SCHEMA_VERSION,
        EXTENSION_SCHEMA_VERSION,
        TARGET_PROTOCOL_SCHEMA_VERSION,
        TARGET_REPORT_SCHEMA_VERSION,
        verify_strategy_correlation_strata_report_extension,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-preregistered-strata-report-public-summary-v1"
)
STATIC_FINGERPRINT = "20260822-strata-report-public-projection-1"


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
        "identity_fields_exposed": False,
        "artifact_hashes_exposed": False,
        "classification_source_values_exposed": False,
        "registry_assets_exposed": False,
        "nested_gates_exposed": False,
        "decision_blockers_exposed": False,
    }


def _unknown_summary() -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SUMMARY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "source": {
            "status": "UNKNOWN",
            "extension_schema": None,
            "base_report_schema_version": None,
            "target_report_schema_version": None,
            "base_protocol_schema_version": None,
            "target_protocol_schema_version": None,
            "entry_count": None,
            "registry_binding_required": None,
        },
        "gap": {
            "status": "SOURCE_INVALID",
            "decision": "UNKNOWN",
            "base_complete_link_block_observed": None,
            "complete_link_blocked_entry_count": None,
            "strata_blocked_entry_count": None,
            "registry_bound_entry_count": None,
            "registry_blocked_entry_count": None,
        },
        "maturity": {
            "status": "UNKNOWN",
            "report_consumer_verification": "BLOCK",
            "registry_asset_evidence": "UNKNOWN",
            "classification_source_binding_check": "UNKNOWN",
            "registry_binding_outcome": "UNKNOWN",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
        },
        "permission": _permission(),
        "redaction": _redaction(),
    }


def _entry_counts(entries: Any) -> dict[str, int]:
    if type(entries) is not list or not entries:
        raise ValueError("strata_report_entries_invalid")
    counts = {
        "complete_link_blocked_entry_count": 0,
        "strata_blocked_entry_count": 0,
        "registry_bound_entry_count": 0,
        "registry_blocked_entry_count": 0,
    }
    for entry in entries:
        if type(entry) is not dict:
            raise ValueError("strata_report_entry_invalid")
        complete_link_gate = entry.get("complete_link_gate")
        strata_gate = entry.get("strata_gate")
        registry_binding = entry.get("registry_binding")
        if not all(
            type(value) is dict
            for value in (complete_link_gate, strata_gate, registry_binding)
        ):
            raise ValueError("strata_report_entry_evidence_invalid")
        complete_link_status = complete_link_gate.get("status")
        strata_status = strata_gate.get("status")
        if complete_link_status not in {"PASS", "BLOCK"}:
            raise ValueError("complete_link_status_invalid")
        if strata_status not in {"PASS", "BLOCK"}:
            raise ValueError("strata_status_invalid")
        if complete_link_status == "BLOCK":
            counts["complete_link_blocked_entry_count"] += 1
        if (
            strata_status == "BLOCK"
            and strata_gate.get("first_blocking_tier") != "BASE_COMPLETE_LINK"
        ):
            counts["strata_blocked_entry_count"] += 1
        if registry_binding.get("status") == "BOUND":
            counts["registry_bound_entry_count"] += 1
        else:
            counts["registry_blocked_entry_count"] += 1
    return counts


def _gap_status(
    *,
    decision: str,
    base_complete_link_block_observed: bool,
    counts: dict[str, int],
) -> str:
    components: list[str] = []
    if (
        base_complete_link_block_observed
        or counts["complete_link_blocked_entry_count"]
    ):
        components.append("BASE_COMPLETE_LINK_BLOCK_OBSERVED")
    if counts["strata_blocked_entry_count"]:
        components.append("PREREGISTERED_STRATA_BLOCK_OBSERVED")
    if counts["registry_blocked_entry_count"]:
        components.append("REGISTRY_BINDING_BLOCK_OBSERVED")
    if decision == "PASS":
        if components:
            raise ValueError("strata_report_pass_with_blocking_gap")
        return "INDEPENDENCE_AND_REGISTRY_BINDING_OBSERVED"
    if decision != "BLOCK" or not components:
        raise ValueError("strata_report_decision_invalid")
    if len(components) == 1:
        return components[0]
    return "MULTIPLE_BLOCKING_GAPS_OBSERVED"


def build_strategy_correlation_strata_report_public_summary(
    source_extension: Any,
    *,
    expected_base_report_hash: Any,
    expected_registry_bindings: Any,
) -> dict[str, Any]:
    try:
        verification = verify_strategy_correlation_strata_report_extension(
            source_extension,
            expected_base_report_hash=expected_base_report_hash,
            expected_registry_bindings=expected_registry_bindings,
        )
        if verification.get("status") != "PASS":
            return _unknown_summary()
        if type(source_extension) is not dict:
            return _unknown_summary()
        decision = verification.get("decision")
        if decision not in {"PASS", "BLOCK"}:
            return _unknown_summary()
        base_extension = source_extension.get("base_complete_link_extension")
        if type(base_extension) is not dict:
            return _unknown_summary()
        base_decision = base_extension.get("decision")
        if base_decision not in {"PASS", "BLOCK"}:
            return _unknown_summary()
        counts = _entry_counts(source_extension.get("entries"))
        base_blocked = base_decision == "BLOCK"
        gap_status = _gap_status(
            decision=decision,
            base_complete_link_block_observed=base_blocked,
            counts=counts,
        )
        entry_count = counts["registry_bound_entry_count"] + counts[
            "registry_blocked_entry_count"
        ]
        return {
            "schema_version": PUBLIC_SUMMARY_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source": {
                "status": "OBSERVED",
                "extension_schema": EXTENSION_SCHEMA_VERSION,
                "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
                "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
                "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
                "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
                "entry_count": entry_count,
                "registry_binding_required": True,
            },
            "gap": {
                "status": gap_status,
                "decision": decision,
                "base_complete_link_block_observed": base_blocked,
                **counts,
            },
            "maturity": {
                "status": (
                    "CONSUMER_EVIDENCE_PASS"
                    if decision == "PASS"
                    else "CONSUMER_EVIDENCE_BLOCK"
                ),
                "report_consumer_verification": "PASS",
                "registry_asset_evidence": "VERIFIED",
                "classification_source_binding_check": "VERIFIED",
                "registry_binding_outcome": (
                    "ALL_BOUND"
                    if counts["registry_blocked_entry_count"] == 0
                    else "BLOCK_OBSERVED"
                ),
                "writer": "NOT_IMPLEMENTED",
                "current": "NOT_ACTIVATED",
            },
            "permission": _permission(),
            "redaction": _redaction(),
        }
    except (MemoryError, RecursionError):
        raise
    except (KeyError, TypeError, ValueError):
        return _unknown_summary()


def verify_strategy_correlation_strata_report_public_summary(
    document: Any,
    *,
    source_extension: Any,
    expected_base_report_hash: Any,
    expected_registry_bindings: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_strata_report_public_summary(
        source_extension,
        expected_base_report_hash=expected_base_report_hash,
        expected_registry_bindings=expected_registry_bindings,
    )
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("strata_report_public_summary_contract_invalid")
    elif not strict_json_contract_equal(document, expected):
        blockers.append("strata_report_public_summary_exact_rebuild_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
    }
