"""Redacted public projection for verified report20 stability evidence."""

from __future__ import annotations

from typing import Any

try:
    from services.strategy_correlation_cluster_stability_report_consumer import (
        BASE_PROTOCOL_SCHEMA_VERSION,
        BASE_REPORT_SCHEMA_VERSION,
        EXTENSION_SCHEMA_VERSION,
        TARGET_PROTOCOL_SCHEMA_VERSION,
        TARGET_REPORT_SCHEMA_VERSION,
        verify_strategy_correlation_cluster_stability_report_extension,
    )
    from services.strict_canonical_json_hash import strict_json_contract_equal
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_cluster_stability_report_consumer import (
        BASE_PROTOCOL_SCHEMA_VERSION,
        BASE_REPORT_SCHEMA_VERSION,
        EXTENSION_SCHEMA_VERSION,
        TARGET_PROTOCOL_SCHEMA_VERSION,
        TARGET_REPORT_SCHEMA_VERSION,
        verify_strategy_correlation_cluster_stability_report_extension,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )


PUBLIC_SUMMARY_SCHEMA = (
    "strategy-correlation-cluster-stability-report-public-summary-v1"
)
STATIC_FINGERPRINT = "20260822-cluster-stability-report-projection-1"


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
        "base_report_extension_exposed": False,
        "source_uncertainty_audits_exposed": False,
        "raw_correlations_exposed": False,
        "selection_cells_exposed": False,
        "nested_gates_exposed": False,
        "decision_blockers_exposed": False,
        "stability_diagnostics_exposed": False,
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
            "stability_gate_count": None,
            "registry_binding_required": None,
            "stability_gate_required": None,
            "external_stability_bindings_required": None,
            "base_global_independence_extension_hash_bound": None,
        },
        "gap": {
            "status": "SOURCE_INVALID",
            "decision": "UNKNOWN",
            "base_global_independence_block_observed": None,
            "stability_gate_pass_count": None,
            "stability_gate_blocked_count": None,
        },
        "maturity": {
            "status": "UNKNOWN",
            "report_consumer_verification": "BLOCK",
            "base_global_independence_evidence": "UNKNOWN",
            "external_stability_binding_check": "UNKNOWN",
            "stability_gate_evidence": "UNKNOWN",
            "stability_outcome": "UNKNOWN",
            "writer": "NOT_IMPLEMENTED",
            "current": "NOT_ACTIVATED",
        },
        "permission": _permission(),
        "redaction": _redaction(),
    }


def _gap_status(
    *,
    decision: str,
    base_blocked: bool,
    stability_blocked_count: int,
) -> str:
    components: list[str] = []
    if base_blocked:
        components.append("BASE_GLOBAL_INDEPENDENCE_BLOCK_OBSERVED")
    if stability_blocked_count:
        components.append("CLUSTER_STABILITY_BLOCK_OBSERVED")
    if decision == "PASS":
        if components:
            raise ValueError("cluster_stability_pass_with_blocking_gap")
        return "CLUSTER_STABILITY_OBSERVED"
    if decision != "BLOCK" or not components:
        raise ValueError("cluster_stability_decision_invalid")
    if len(components) == 1:
        return components[0]
    return "MULTIPLE_BLOCKING_GAPS_OBSERVED"


def build_strategy_correlation_cluster_stability_report_public_summary(
    source_extension: Any,
    *,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
) -> dict[str, Any]:
    try:
        verification = verify_strategy_correlation_cluster_stability_report_extension(
            source_extension,
            expected_base_report_hash=expected_base_report_hash,
            expected_global_independence_extension_hash=(
                expected_global_independence_extension_hash
            ),
            expected_registry_bindings=expected_registry_bindings,
            expected_stability_bindings=expected_stability_bindings,
        )
        if verification.get("status") != "PASS":
            return _unknown_summary()
        if type(source_extension) is not dict:
            return _unknown_summary()
        base_extension = source_extension.get(
            "base_global_independence_extension"
        )
        if type(base_extension) is not dict:
            return _unknown_summary()
        decision = verification.get("decision")
        base_decision = base_extension.get("decision")
        gate_count = verification.get("stability_gate_count")
        gate_pass_count = verification.get("stability_gate_pass_count")
        if decision not in {"PASS", "BLOCK"}:
            return _unknown_summary()
        if base_decision not in {"PASS", "BLOCK"}:
            return _unknown_summary()
        if (
            type(gate_count) is not int
            or type(gate_pass_count) is not int
            or gate_count <= 0
            or gate_pass_count < 0
            or gate_pass_count > gate_count
        ):
            return _unknown_summary()
        gate_blocked_count = gate_count - gate_pass_count
        base_blocked = base_decision == "BLOCK"
        gap_status = _gap_status(
            decision=decision,
            base_blocked=base_blocked,
            stability_blocked_count=gate_blocked_count,
        )
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
                "stability_gate_count": gate_count,
                "registry_binding_required": True,
                "stability_gate_required": True,
                "external_stability_bindings_required": True,
                "base_global_independence_extension_hash_bound": True,
            },
            "gap": {
                "status": gap_status,
                "decision": decision,
                "base_global_independence_block_observed": base_blocked,
                "stability_gate_pass_count": gate_pass_count,
                "stability_gate_blocked_count": gate_blocked_count,
            },
            "maturity": {
                "status": (
                    "CONSUMER_EVIDENCE_PASS"
                    if decision == "PASS"
                    else "CONSUMER_EVIDENCE_BLOCK"
                ),
                "report_consumer_verification": "PASS",
                "base_global_independence_evidence": "VERIFIED",
                "external_stability_binding_check": "VERIFIED",
                "stability_gate_evidence": "VERIFIED",
                "stability_outcome": (
                    "ALL_PASS"
                    if gate_blocked_count == 0
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


def verify_strategy_correlation_cluster_stability_report_public_summary(
    document: Any,
    *,
    source_extension: Any,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_stability_report_public_summary(
        source_extension,
        expected_base_report_hash=expected_base_report_hash,
        expected_global_independence_extension_hash=(
            expected_global_independence_extension_hash
        ),
        expected_registry_bindings=expected_registry_bindings,
        expected_stability_bindings=expected_stability_bindings,
    )
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("cluster_stability_report_public_summary_contract_invalid")
    elif not strict_json_contract_equal(document, expected):
        blockers.append(
            "cluster_stability_report_public_summary_exact_rebuild_mismatch"
        )
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
    }
