"""Verifier-only report20 extension for within-cluster stability evidence."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_stability import (
    GATE_SCHEMA_VERSION as STABILITY_GATE_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_stability_gate,
)
from exchange_terminal.services.strategy_correlation_global_independence_report_consumer import (
    EXTENSION_SCHEMA_VERSION as GLOBAL_INDEPENDENCE_EXTENSION_SCHEMA_VERSION,
    verify_strategy_correlation_global_independence_report_extension,
)


BASE_REPORT_SCHEMA_VERSION = 19
BASE_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v8"
TARGET_REPORT_SCHEMA_VERSION = 20
TARGET_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v9"
EXTENSION_SCHEMA_VERSION = "strategy-research-cluster-stability-extension-v1"
VERIFICATION_SCHEMA_VERSION = (
    "strategy-research-cluster-stability-extension-verification-v1"
)

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_ENTRY_FIELDS = {
    "strategy_id",
    "variant_id",
    "lane",
    "stability_gate",
    "stability_gate_hash",
}
_BINDING_FIELDS = {
    "strategy_id",
    "variant_id",
    "lane",
    "source_uncertainty_audit",
    "correlation_matrix",
    "selection_cells",
    "expected_stability_gate_hash",
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


def _binding_index(bindings: Any) -> dict[tuple[str, str, str], dict[str, Any]] | None:
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
            or not _is_sha256(binding.get("expected_stability_gate_hash"))
            or identity in indexed
        ):
            return None
        indexed[identity] = binding
    return indexed


def _base_entry_index(
    base_extension: Any,
) -> tuple[list[tuple[str, str, str]], dict[tuple[str, str, str], dict[str, Any]]] | None:
    entries = base_extension.get("entries") if type(base_extension) is dict else None
    if type(entries) is not list:
        return None
    order: list[tuple[str, str, str]] = []
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in entries:
        identity = _identity(entry)
        if (
            identity is None
            or identity in indexed
            or type(entry.get("source_preregistration")) is not dict
            or type(entry.get("complete_link_gate")) is not dict
        ):
            return None
        order.append(identity)
        indexed[identity] = entry
    return order, indexed


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
            or type(entry.get("stability_gate")) is not dict
            or not _is_sha256(entry.get("stability_gate_hash"))
            or identity in indexed
        ):
            return None
        indexed[identity] = entry
    return indexed


def _verification_result(
    blockers: list[str],
    *,
    decision: str = "BLOCK",
    stability_gate_count: int = 0,
    stability_gate_pass_count: int = 0,
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
        "stability_gate_count": stability_gate_count,
        "stability_gate_pass_count": stability_gate_pass_count,
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def verify_strategy_correlation_cluster_stability_report_extension(
    document: Any,
    *,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification_result(["cluster_stability_extension_invalid"])
    if strict_research_authority_violations(document):
        blockers.append("research_authority_violation")

    base_extension = document.get("base_global_independence_extension")
    try:
        base_verification = (
            verify_strategy_correlation_global_independence_report_extension(
                base_extension,
                expected_base_report_hash=expected_base_report_hash,
                expected_registry_bindings=expected_registry_bindings,
            )
            if type(base_extension) is dict
            else {"status": "BLOCK", "decision": "BLOCK"}
        )
    except (TypeError, ValueError):
        base_verification = {"status": "BLOCK", "decision": "BLOCK"}
    if base_verification.get("status") != "PASS":
        blockers.append("base_global_independence_extension_invalid")
    if not _is_sha256(expected_base_report_hash):
        blockers.append("expected_base_report_hash_invalid")
    if (
        not _is_sha256(expected_global_independence_extension_hash)
        or type(base_extension) is not dict
        or base_extension.get("extension_hash")
        != expected_global_independence_extension_hash
    ):
        blockers.append("global_independence_extension_hash_mismatch")

    bindings = _binding_index(expected_stability_bindings)
    if bindings is None:
        blockers.append("stability_bindings_invalid")
    base_entries = _base_entry_index(base_extension)
    if base_entries is None:
        blockers.append("base_global_independence_entries_invalid")
    document_entries = _document_entry_index(document)
    if document_entries is None:
        blockers.append("cluster_stability_entries_invalid")

    normalized_entries: list[dict[str, Any]] = []
    gate_decisions: dict[tuple[str, str, str], str] = {}
    if bindings is not None and base_entries is not None and document_entries is not None:
        order, base_index = base_entries
        expected_identities = set(base_index)
        if set(bindings) != expected_identities or set(document_entries) != expected_identities:
            blockers.append("cluster_stability_identity_set_mismatch")
        else:
            for identity in order:
                base_entry = base_index[identity]
                extension_entry = document_entries[identity]
                binding = bindings[identity]
                gate = extension_entry["stability_gate"]
                gate_hash = extension_entry["stability_gate_hash"]
                if (
                    gate.get("gate_hash") != gate_hash
                    or gate_hash != binding["expected_stability_gate_hash"]
                ):
                    blockers.append(
                        "cluster_stability_gate_hash_mismatch:" + ":".join(identity)
                    )
                    continue
                try:
                    gate_verification = verify_strategy_correlation_cluster_stability_gate(
                        gate,
                        source_uncertainty_audit=binding["source_uncertainty_audit"],
                        complete_link_gate=base_entry["complete_link_gate"],
                        preregistration=base_entry["source_preregistration"],
                        correlation_matrix=binding["correlation_matrix"],
                        selection_cells=binding["selection_cells"],
                        strategy_id=identity[0],
                        variant_id=identity[1],
                        lane=identity[2],
                    )
                except (TypeError, ValueError):
                    gate_verification = {"status": "BLOCK", "decision": "BLOCK"}
                if gate_verification.get("status") != "PASS":
                    blockers.append(
                        "cluster_stability_gate_invalid:" + ":".join(identity)
                    )
                    continue
                gate_decisions[identity] = gate_verification.get("decision", "BLOCK")
                normalized_entries.append(
                    {
                        "strategy_id": identity[0],
                        "variant_id": identity[1],
                        "lane": identity[2],
                        "stability_gate": gate,
                        "stability_gate_hash": gate_hash,
                    }
                )

    decision = "BLOCK"
    decision_blockers: list[str] = []
    if not blockers and base_entries is not None:
        order, _ = base_entries
        if base_verification.get("decision") != "PASS":
            decision_blockers.append("base_global_independence_decision_blocked")
        decision_blockers.extend(
            "cluster_stability_gate_blocked:" + ":".join(identity)
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
            "base_global_independence_extension": base_extension,
            "base_global_independence_extension_hash": (
                expected_global_independence_extension_hash
            ),
            "registry_binding_required": True,
            "stability_gate_required": True,
            "external_stability_bindings_required": True,
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
            blockers.append("cluster_stability_extension_contract_invalid")
        else:
            if not strict_json_contract_equal(document, expected):
                blockers.append("cluster_stability_extension_contract_invalid")

    return _verification_result(
        blockers,
        decision=decision,
        stability_gate_count=len(normalized_entries),
        stability_gate_pass_count=sum(
            value == "PASS" for value in gate_decisions.values()
        ),
    )


__all__ = [
    "BASE_PROTOCOL_SCHEMA_VERSION",
    "BASE_REPORT_SCHEMA_VERSION",
    "EXTENSION_SCHEMA_VERSION",
    "GLOBAL_INDEPENDENCE_EXTENSION_SCHEMA_VERSION",
    "STABILITY_GATE_SCHEMA_VERSION",
    "TARGET_PROTOCOL_SCHEMA_VERSION",
    "TARGET_REPORT_SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "verify_strategy_correlation_cluster_stability_report_extension",
]
