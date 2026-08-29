"""Verifier-only report21 extension for preregistered temporal cluster stability."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_stability_report_consumer import (
    EXTENSION_SCHEMA_VERSION as BASE_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION as BASE_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION as BASE_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_stability_report_extension,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability import (
    GATE_SCHEMA_VERSION as TEMPORAL_STABILITY_GATE_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_stability_gate,
)


TARGET_REPORT_SCHEMA_VERSION = 21
TARGET_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v10"
EXTENSION_SCHEMA_VERSION = (
    "strategy-research-cluster-temporal-stability-extension-v1"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-research-cluster-temporal-stability-extension-verification-v1"
)

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_ENTRY_FIELDS = {
    "strategy_id",
    "variant_id",
    "lane",
    "temporal_stability_gate",
    "temporal_stability_gate_hash",
}
_BINDING_FIELDS = {
    "strategy_id",
    "variant_id",
    "lane",
    "source_uncertainty_audit",
    "correlation_matrix",
    "selection_cells",
    "expected_temporal_stability_gate_hash",
}


def _identity(document: Any) -> tuple[str, str, str] | None:
    if type(document) is not dict:
        return None
    values = tuple(document.get(field) for field in ("strategy_id", "variant_id", "lane"))
    if not all(type(value) is str and value for value in values):
        return None
    return values


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _binding_index(
    bindings: Any,
) -> dict[tuple[str, str, str], dict[str, Any]] | None:
    if type(bindings) is not list:
        return None
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for binding in bindings:
        identity = _identity(binding)
        if (
            identity is None
            or type(binding) is not dict
            or set(binding) != _BINDING_FIELDS
            or type(binding.get("source_uncertainty_audit")) is not dict
            or type(binding.get("correlation_matrix")) is not dict
            or type(binding.get("selection_cells")) is not list
            or not _is_sha256(
                binding.get("expected_temporal_stability_gate_hash")
            )
            or identity in indexed
        ):
            return None
        indexed[identity] = binding
    return indexed


def _base_entry_index(
    base_extension: Any,
) -> tuple[
    list[tuple[str, str, str]],
    dict[tuple[str, str, str], dict[str, Any]],
    dict[tuple[str, str, str], dict[str, Any]],
] | None:
    if type(base_extension) is not dict:
        return None
    base_entries = base_extension.get("entries")
    source_extension = base_extension.get("base_global_independence_extension")
    source_entries = (
        source_extension.get("entries") if type(source_extension) is dict else None
    )
    if type(base_entries) is not list or type(source_entries) is not list:
        return None
    order: list[tuple[str, str, str]] = []
    base_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    source_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in base_entries:
        identity = _identity(entry)
        if (
            identity is None
            or identity in base_index
            or type(entry.get("stability_gate")) is not dict
        ):
            return None
        order.append(identity)
        base_index[identity] = entry
    for entry in source_entries:
        identity = _identity(entry)
        if (
            identity is None
            or identity in source_index
            or type(entry.get("source_preregistration")) is not dict
            or type(entry.get("complete_link_gate")) is not dict
        ):
            return None
        source_index[identity] = entry
    if set(base_index) != set(source_index):
        return None
    return order, base_index, source_index


def _document_entry_index(
    document: Any,
) -> dict[tuple[str, str, str], dict[str, Any]] | None:
    entries = document.get("entries") if type(document) is dict else None
    if type(entries) is not list:
        return None
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in entries:
        identity = _identity(entry)
        if (
            identity is None
            or type(entry) is not dict
            or set(entry) != _ENTRY_FIELDS
            or type(entry.get("temporal_stability_gate")) is not dict
            or not _is_sha256(entry.get("temporal_stability_gate_hash"))
            or identity in indexed
        ):
            return None
        indexed[identity] = entry
    return indexed


def _verification_result(
    blockers: list[str],
    *,
    decision: str = "BLOCK",
    temporal_stability_gate_count: int = 0,
    temporal_stability_gate_pass_count: int = 0,
) -> dict[str, Any]:
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "decision": decision if status == "PASS" else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "temporal_stability_gate_count": temporal_stability_gate_count,
        "temporal_stability_gate_pass_count": temporal_stability_gate_pass_count,
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def verify_strategy_correlation_cluster_temporal_stability_report_extension(
    document: Any,
    *,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    expected_temporal_stability_bindings: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification_result(["cluster_temporal_stability_extension_invalid"])
    if strict_research_authority_violations(document):
        blockers.append("research_authority_violation")

    base_extension = document.get("base_cluster_stability_extension")
    try:
        base_verification = (
            verify_strategy_correlation_cluster_stability_report_extension(
                base_extension,
                expected_base_report_hash=expected_base_report_hash,
                expected_global_independence_extension_hash=(
                    expected_global_independence_extension_hash
                ),
                expected_registry_bindings=expected_registry_bindings,
                expected_stability_bindings=expected_stability_bindings,
            )
            if type(base_extension) is dict
            else {"status": "BLOCK", "decision": "BLOCK"}
        )
    except (KeyError, TypeError, ValueError):
        base_verification = {"status": "BLOCK", "decision": "BLOCK"}
    if base_verification.get("status") != "PASS":
        blockers.append("base_cluster_stability_extension_invalid")
    if not _is_sha256(expected_base_report_hash):
        blockers.append("expected_base_report_hash_invalid")
    if (
        not _is_sha256(expected_cluster_stability_extension_hash)
        or type(base_extension) is not dict
        or base_extension.get("extension_hash")
        != expected_cluster_stability_extension_hash
    ):
        blockers.append("cluster_stability_extension_hash_mismatch")

    bindings = _binding_index(expected_temporal_stability_bindings)
    if bindings is None:
        blockers.append("temporal_stability_bindings_invalid")
    base_entries = _base_entry_index(base_extension)
    if base_entries is None:
        blockers.append("base_cluster_stability_entries_invalid")
    document_entries = _document_entry_index(document)
    if document_entries is None:
        blockers.append("cluster_temporal_stability_entries_invalid")

    normalized_entries: list[dict[str, Any]] = []
    gate_decisions: dict[tuple[str, str, str], str] = {}
    if bindings is not None and base_entries is not None and document_entries is not None:
        order, base_index, source_index = base_entries
        expected_identities = set(base_index)
        if set(bindings) != expected_identities or set(document_entries) != expected_identities:
            blockers.append("cluster_temporal_stability_identity_set_mismatch")
        else:
            for identity in order:
                base_entry = base_index[identity]
                source_entry = source_index[identity]
                extension_entry = document_entries[identity]
                binding = bindings[identity]
                gate = extension_entry["temporal_stability_gate"]
                gate_hash = extension_entry["temporal_stability_gate_hash"]
                if (
                    gate.get("gate_hash") != gate_hash
                    or gate_hash
                    != binding["expected_temporal_stability_gate_hash"]
                ):
                    blockers.append(
                        "cluster_temporal_stability_gate_hash_mismatch:"
                        + ":".join(identity)
                    )
                    continue
                try:
                    gate_verification = (
                        verify_strategy_correlation_cluster_temporal_stability_gate(
                            gate,
                            source_uncertainty_audit=binding[
                                "source_uncertainty_audit"
                            ],
                            full_window_stability_gate=base_entry[
                                "stability_gate"
                            ],
                            complete_link_gate=source_entry["complete_link_gate"],
                            preregistration=source_entry["source_preregistration"],
                            correlation_matrix=binding["correlation_matrix"],
                            selection_cells=binding["selection_cells"],
                            strategy_id=identity[0],
                            variant_id=identity[1],
                            lane=identity[2],
                        )
                    )
                except (KeyError, TypeError, ValueError):
                    gate_verification = {
                        "status": "BLOCK",
                        "decision_status": "BLOCK",
                    }
                if gate_verification.get("status") != "PASS":
                    blockers.append(
                        "cluster_temporal_stability_gate_invalid:"
                        + ":".join(identity)
                    )
                    continue
                gate_decisions[identity] = gate_verification.get(
                    "decision_status", "BLOCK"
                )
                normalized_entries.append(
                    {
                        "strategy_id": identity[0],
                        "variant_id": identity[1],
                        "lane": identity[2],
                        "temporal_stability_gate": gate,
                        "temporal_stability_gate_hash": gate_hash,
                    }
                )

    decision = "BLOCK"
    decision_blockers: list[str] = []
    if not blockers and base_entries is not None:
        order, _, _ = base_entries
        if base_verification.get("decision") != "PASS":
            decision_blockers.append("base_cluster_stability_decision_blocked")
        decision_blockers.extend(
            "cluster_temporal_stability_gate_blocked:" + ":".join(identity)
            for identity in order
            if gate_decisions.get(identity) != "PASS"
        )
        decision = "PASS" if not decision_blockers else "BLOCK"
        expected = {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "base_report_hash": expected_base_report_hash,
            "base_cluster_stability_extension": base_extension,
            "base_cluster_stability_extension_hash": (
                expected_cluster_stability_extension_hash
            ),
            "registry_bindings_required": True,
            "stability_bindings_required": True,
            "temporal_stability_gate_required": True,
            "external_temporal_stability_bindings_required": True,
            "entries": normalized_entries,
            "decision": decision,
            "decision_blockers": decision_blockers,
            "consumer_only": True,
            "requires_new_report_schema": True,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": dict(_PERMISSIONS),
        }
        try:
            expected = seal_strict_canonical_document(expected, "extension_hash")
        except (TypeError, ValueError):
            blockers.append("cluster_temporal_stability_extension_contract_invalid")
        else:
            if not strict_json_contract_equal(document, expected):
                blockers.append("cluster_temporal_stability_extension_contract_invalid")

    return _verification_result(
        blockers,
        decision=decision,
        temporal_stability_gate_count=len(normalized_entries),
        temporal_stability_gate_pass_count=sum(
            value == "PASS" for value in gate_decisions.values()
        ),
    )


__all__ = [
    "BASE_EXTENSION_SCHEMA_VERSION",
    "BASE_PROTOCOL_SCHEMA_VERSION",
    "BASE_REPORT_SCHEMA_VERSION",
    "EXTENSION_SCHEMA_VERSION",
    "TARGET_PROTOCOL_SCHEMA_VERSION",
    "TARGET_REPORT_SCHEMA_VERSION",
    "TEMPORAL_STABILITY_GATE_SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "verify_strategy_correlation_cluster_temporal_stability_report_extension",
]
