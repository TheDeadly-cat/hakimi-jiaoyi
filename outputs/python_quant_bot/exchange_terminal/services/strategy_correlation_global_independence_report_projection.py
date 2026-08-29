"""Redacted public projection for verified report19 independence evidence."""

from __future__ import annotations

from typing import Any

try:
    from services.strategy_correlation_global_independence_report_consumer import (
        BASE_PROTOCOL_SCHEMA_VERSION,
        BASE_REPORT_SCHEMA_VERSION,
        EXTENSION_SCHEMA_VERSION,
        TARGET_PROTOCOL_SCHEMA_VERSION,
        TARGET_REPORT_SCHEMA_VERSION,
        verify_strategy_correlation_global_independence_report_extension,
    )
    from services.strict_canonical_json_hash import strict_json_contract_equal
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_global_independence_report_consumer import (
        BASE_PROTOCOL_SCHEMA_VERSION,
        BASE_REPORT_SCHEMA_VERSION,
        EXTENSION_SCHEMA_VERSION,
        TARGET_PROTOCOL_SCHEMA_VERSION,
        TARGET_REPORT_SCHEMA_VERSION,
        verify_strategy_correlation_global_independence_report_extension,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-global-independence-report-public-summary-v1"
)
STATIC_FINGERPRINT = "20260822-global-independence-report-projection-1"


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
        "source_registrations_exposed": False,
        "nested_gates_exposed": False,
        "decision_blockers_exposed": False,
        "global_graph_details_exposed": False,
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
            "global_independence_required": None,
            "registry_binding_required": None,
        },
        "gap": {
            "status": "SOURCE_INVALID",
            "decision": "UNKNOWN",
            "base_complete_link_block_observed": None,
            "strata_blocked_entry_count": None,
            "registry_bound_entry_count": None,
            "registry_blocked_entry_count": None,
            "global_independence_blocked_entry_count": None,
        },
        "maturity": {
            "status": "UNKNOWN",
            "report_consumer_verification": "BLOCK",
            "base_strata_evidence": "UNKNOWN",
            "global_independence_evidence": "UNKNOWN",
            "registry_asset_evidence": "UNKNOWN",
            "classification_source_binding_check": "UNKNOWN",
            "registry_binding_outcome": "UNKNOWN",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
        },
        "permission": _permission(),
        "redaction": _redaction(),
    }


def _evidence_counts(source_extension: dict[str, Any]) -> dict[str, Any]:
    entries = source_extension.get("entries")
    base_extension = source_extension.get("base_strata_extension")
    if type(entries) is not list or not entries or type(base_extension) is not dict:
        raise ValueError("global_independence_report_evidence_invalid")
    base_entries = base_extension.get("entries")
    base_complete_link_extension = base_extension.get(
        "base_complete_link_extension"
    )
    if (
        type(base_entries) is not list
        or not base_entries
        or type(base_complete_link_extension) is not dict
    ):
        raise ValueError("base_strata_report_evidence_invalid")
    base_complete_link_decision = base_complete_link_extension.get("decision")
    base_strata_decision = base_extension.get("decision")
    if base_complete_link_decision not in {"PASS", "BLOCK"}:
        raise ValueError("base_complete_link_decision_invalid")
    if base_strata_decision not in {"PASS", "BLOCK"}:
        raise ValueError("base_strata_decision_invalid")

    strata_blocked = 0
    registry_bound = 0
    registry_blocked = 0
    for entry in base_entries:
        if type(entry) is not dict:
            raise ValueError("base_strata_entry_invalid")
        strata_gate = entry.get("strata_gate")
        registry_binding = entry.get("registry_binding")
        if type(strata_gate) is not dict or type(registry_binding) is not dict:
            raise ValueError("base_strata_entry_evidence_invalid")
        strata_status = strata_gate.get("status")
        if strata_status not in {"PASS", "BLOCK"}:
            raise ValueError("base_strata_gate_status_invalid")
        if (
            strata_status == "BLOCK"
            and strata_gate.get("first_blocking_tier") != "BASE_COMPLETE_LINK"
        ):
            strata_blocked += 1
        if registry_binding.get("status") == "BOUND":
            registry_bound += 1
        else:
            registry_blocked += 1

    global_blocked = 0
    for entry in entries:
        if type(entry) is not dict:
            raise ValueError("global_independence_entry_invalid")
        gate = entry.get("global_independence_gate")
        if type(gate) is not dict:
            raise ValueError("global_independence_gate_invalid")
        status = gate.get("status")
        if status not in {"PASS", "BLOCK"}:
            raise ValueError("global_independence_gate_status_invalid")
        if (
            status == "BLOCK"
            and gate.get("first_blocking_tier") != "BASE_STRATA_GATE"
        ):
            global_blocked += 1

    return {
        "entry_count": len(entries),
        "base_complete_link_block_observed": (
            base_complete_link_decision == "BLOCK"
        ),
        "base_strata_block_observed": base_strata_decision == "BLOCK",
        "strata_blocked_entry_count": strata_blocked,
        "registry_bound_entry_count": registry_bound,
        "registry_blocked_entry_count": registry_blocked,
        "global_independence_blocked_entry_count": global_blocked,
    }


def _gap_status(*, decision: str, counts: dict[str, Any]) -> str:
    components: list[str] = []
    if counts["base_complete_link_block_observed"]:
        components.append("BASE_COMPLETE_LINK_BLOCK_OBSERVED")
    if counts["strata_blocked_entry_count"]:
        components.append("PREREGISTERED_STRATA_BLOCK_OBSERVED")
    if counts["registry_blocked_entry_count"]:
        components.append("REGISTRY_BINDING_BLOCK_OBSERVED")
    if counts["global_independence_blocked_entry_count"]:
        components.append("GLOBAL_INDEPENDENCE_BLOCK_OBSERVED")
    if decision == "PASS":
        if components or counts["base_strata_block_observed"]:
            raise ValueError("global_independence_pass_with_blocking_gap")
        return "GLOBAL_INDEPENDENCE_OBSERVED"
    if decision != "BLOCK" or not components:
        raise ValueError("global_independence_decision_invalid")
    if len(components) == 1:
        return components[0]
    return "MULTIPLE_BLOCKING_GAPS_OBSERVED"


def build_strategy_correlation_global_independence_report_public_summary(
    source_extension: Any,
    *,
    expected_base_report_hash: Any,
    expected_registry_bindings: Any,
) -> dict[str, Any]:
    try:
        verification = (
            verify_strategy_correlation_global_independence_report_extension(
                source_extension,
                expected_base_report_hash=expected_base_report_hash,
                expected_registry_bindings=expected_registry_bindings,
            )
        )
        if verification.get("status") != "PASS":
            return _unknown_summary()
        if type(source_extension) is not dict:
            return _unknown_summary()
        decision = verification.get("decision")
        if decision not in {"PASS", "BLOCK"}:
            return _unknown_summary()
        counts = _evidence_counts(source_extension)
        gap_status = _gap_status(decision=decision, counts=counts)
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
                "entry_count": counts["entry_count"],
                "global_independence_required": True,
                "registry_binding_required": True,
            },
            "gap": {
                "status": gap_status,
                "decision": decision,
                "base_complete_link_block_observed": counts[
                    "base_complete_link_block_observed"
                ],
                "strata_blocked_entry_count": counts[
                    "strata_blocked_entry_count"
                ],
                "registry_bound_entry_count": counts[
                    "registry_bound_entry_count"
                ],
                "registry_blocked_entry_count": counts[
                    "registry_blocked_entry_count"
                ],
                "global_independence_blocked_entry_count": counts[
                    "global_independence_blocked_entry_count"
                ],
            },
            "maturity": {
                "status": (
                    "CONSUMER_EVIDENCE_PASS"
                    if decision == "PASS"
                    else "CONSUMER_EVIDENCE_BLOCK"
                ),
                "report_consumer_verification": "PASS",
                "base_strata_evidence": "VERIFIED",
                "global_independence_evidence": "VERIFIED",
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


def verify_strategy_correlation_global_independence_report_public_summary(
    document: Any,
    *,
    source_extension: Any,
    expected_base_report_hash: Any,
    expected_registry_bindings: Any,
) -> dict[str, Any]:
    expected = (
        build_strategy_correlation_global_independence_report_public_summary(
            source_extension,
            expected_base_report_hash=expected_base_report_hash,
            expected_registry_bindings=expected_registry_bindings,
        )
    )
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append(
            "global_independence_report_public_summary_contract_invalid"
        )
    elif not strict_json_contract_equal(document, expected):
        blockers.append(
            "global_independence_report_public_summary_exact_rebuild_mismatch"
        )
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
    }
