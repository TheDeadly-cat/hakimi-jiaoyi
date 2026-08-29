"""Verifier-only report22 extension for exact temporal date-grid gates."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid import (
    GATE_SCHEMA_VERSION as TEMPORAL_DATE_GRID_GATE_SCHEMA_VERSION,
    evaluate_strategy_correlation_cluster_temporal_date_grid_gate,
    verify_strategy_correlation_cluster_temporal_date_grid_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_protocol import (
    TARGET_EXTENSION_SCHEMA_VERSION as EXTENSION_SCHEMA_VERSION,
    TARGET_EXTENSION_VERIFICATION_SCHEMA_VERSION as VERIFICATION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_consumer import (
    EXTENSION_SCHEMA_VERSION as BASE_EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION as BASE_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION as BASE_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_stability_report_extension,
)


_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_ENTRY_FIELDS = {
    "strategy_id",
    "variant_id",
    "lane",
    "temporal_date_grid_gate",
    "temporal_date_grid_gate_hash",
}
_TEMPORAL_BINDING_FIELDS = {
    "strategy_id",
    "variant_id",
    "lane",
    "source_uncertainty_audit",
    "correlation_matrix",
    "selection_cells",
    "expected_temporal_stability_gate_hash",
}
_DATE_GRID_BINDING_FIELDS = {
    "strategy_id",
    "variant_id",
    "lane",
    "expected_temporal_date_grid_gate_hash",
}


def _identity(value: Any) -> tuple[str, str, str] | None:
    if type(value) is not dict:
        return None
    identity = tuple(
        value.get(field) for field in ("strategy_id", "variant_id", "lane")
    )
    if not all(type(part) is str and part for part in identity):
        return None
    return identity  # type: ignore[return-value]


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _binding_index(
    values: Any,
    *,
    fields: set[str],
    hash_field: str,
) -> dict[tuple[str, str, str], dict[str, Any]] | None:
    if type(values) is not list:
        return None
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        identity = _identity(value)
        if (
            identity is None
            or type(value) is not dict
            or set(value) != fields
            or not _is_sha256(value.get(hash_field))
            or identity in indexed
        ):
            return None
        if fields == _TEMPORAL_BINDING_FIELDS and (
            type(value.get("source_uncertainty_audit")) is not dict
            or type(value.get("correlation_matrix")) is not dict
            or type(value.get("selection_cells")) is not list
        ):
            return None
        indexed[identity] = value
    return indexed


def _entry_index(
    values: Any,
    *,
    required_mapping_fields: tuple[str, ...],
    exact_fields: set[str] | None = None,
) -> tuple[
    list[tuple[str, str, str]],
    dict[tuple[str, str, str], dict[str, Any]],
] | None:
    if type(values) is not list or not values:
        return None
    order: list[tuple[str, str, str]] = []
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        identity = _identity(value)
        if (
            identity is None
            or identity in indexed
            or (
                exact_fields is not None
                and (type(value) is not dict or set(value) != exact_fields)
            )
            or any(type(value.get(field)) is not dict for field in required_mapping_fields)
        ):
            return None
        order.append(identity)
        indexed[identity] = value
    return order, indexed


def _base_indexes(
    report21_extension: Any,
) -> tuple[
    list[tuple[str, str, str]],
    dict[tuple[str, str, str], dict[str, Any]],
    dict[tuple[str, str, str], dict[str, Any]],
    dict[tuple[str, str, str], dict[str, Any]],
] | None:
    if type(report21_extension) is not dict:
        return None
    report_entries = _entry_index(
        report21_extension.get("entries"),
        required_mapping_fields=("temporal_stability_gate",),
    )
    report20 = report21_extension.get("base_cluster_stability_extension")
    report20 = report20 if type(report20) is dict else {}
    stability_entries = _entry_index(
        report20.get("entries"),
        required_mapping_fields=("stability_gate",),
    )
    report19 = report20.get("base_global_independence_extension")
    report19 = report19 if type(report19) is dict else {}
    source_entries = _entry_index(
        report19.get("entries"),
        required_mapping_fields=("source_preregistration", "complete_link_gate"),
    )
    if (
        report_entries is None
        or stability_entries is None
        or source_entries is None
    ):
        return None
    order, report_index = report_entries
    _, stability_index = stability_entries
    _, source_index = source_entries
    if set(report_index) != set(stability_index) or set(report_index) != set(
        source_index
    ):
        return None
    return order, report_index, stability_index, source_index


def _document_entry_index(
    document: Any,
) -> dict[tuple[str, str, str], dict[str, Any]] | None:
    entries = document.get("entries") if type(document) is dict else None
    result = _entry_index(
        entries,
        required_mapping_fields=("temporal_date_grid_gate",),
        exact_fields=_ENTRY_FIELDS,
    )
    if result is None:
        return None
    _, indexed = result
    for entry in indexed.values():
        if not _is_sha256(entry.get("temporal_date_grid_gate_hash")):
            return None
    return indexed


def _verification_result(
    blockers: list[str],
    *,
    decision: str = "BLOCK",
    date_grid_gate_count: int = 0,
    date_grid_gate_pass_count: int = 0,
) -> dict[str, Any]:
    unique = list(dict.fromkeys(blockers))
    status = "PASS" if not unique else "BLOCK"
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "decision": decision if status == "PASS" else "BLOCK",
        "blockers": unique,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "date_grid_gate_count": date_grid_gate_count,
        "date_grid_gate_pass_count": date_grid_gate_pass_count,
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def verify_strategy_correlation_cluster_temporal_date_grid_report_extension(
    document: Any,
    *,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_report21_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    expected_temporal_stability_bindings: Any,
    expected_temporal_date_grid_bindings: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification_result(["temporal_date_grid_extension_invalid"])
    if strict_research_authority_violations(document):
        blockers.append("research_authority_violation")

    report21 = document.get("base_report21_extension")
    try:
        base_verification = (
            verify_strategy_correlation_cluster_temporal_stability_report_extension(
                report21,
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
            if type(report21) is dict
            else {"status": "BLOCK", "decision": "BLOCK"}
        )
    except (KeyError, TypeError, ValueError):
        base_verification = {"status": "BLOCK", "decision": "BLOCK"}
    if base_verification.get("status") != "PASS":
        blockers.append("base_report21_extension_invalid")
    if not _is_sha256(expected_base_report_hash):
        blockers.append("expected_base_report_hash_invalid")
    if (
        not _is_sha256(expected_report21_extension_hash)
        or type(report21) is not dict
        or report21.get("extension_hash") != expected_report21_extension_hash
    ):
        blockers.append("report21_extension_hash_mismatch")

    temporal_bindings = _binding_index(
        expected_temporal_stability_bindings,
        fields=_TEMPORAL_BINDING_FIELDS,
        hash_field="expected_temporal_stability_gate_hash",
    )
    if temporal_bindings is None:
        blockers.append("temporal_stability_bindings_invalid")
    date_grid_bindings = _binding_index(
        expected_temporal_date_grid_bindings,
        fields=_DATE_GRID_BINDING_FIELDS,
        hash_field="expected_temporal_date_grid_gate_hash",
    )
    if date_grid_bindings is None:
        blockers.append("temporal_date_grid_bindings_invalid")
    base_indexes = _base_indexes(report21)
    if base_indexes is None:
        blockers.append("base_report21_entries_invalid")
    document_entries = _document_entry_index(document)
    if document_entries is None:
        blockers.append("temporal_date_grid_entries_invalid")

    normalized_entries: list[dict[str, Any]] = []
    gate_decisions: dict[tuple[str, str, str], str] = {}
    if (
        temporal_bindings is not None
        and date_grid_bindings is not None
        and base_indexes is not None
        and document_entries is not None
    ):
        order, report_index, stability_index, source_index = base_indexes
        expected_identities = set(report_index)
        if (
            set(temporal_bindings) != expected_identities
            or set(date_grid_bindings) != expected_identities
            or set(document_entries) != expected_identities
        ):
            blockers.append("temporal_date_grid_identity_set_mismatch")
        else:
            for identity in order:
                report_entry = report_index[identity]
                stability_entry = stability_index[identity]
                source_entry = source_index[identity]
                temporal_binding = temporal_bindings[identity]
                date_grid_binding = date_grid_bindings[identity]
                extension_entry = document_entries[identity]
                gate = extension_entry["temporal_date_grid_gate"]
                gate_hash = extension_entry["temporal_date_grid_gate_hash"]
                if (
                    gate.get("gate_hash") != gate_hash
                    or gate_hash
                    != date_grid_binding[
                        "expected_temporal_date_grid_gate_hash"
                    ]
                ):
                    blockers.append(
                        "temporal_date_grid_gate_hash_mismatch:"
                        + ":".join(identity)
                    )
                    continue
                try:
                    expected_gate = (
                        evaluate_strategy_correlation_cluster_temporal_date_grid_gate(
                            temporal_binding["source_uncertainty_audit"],
                            report_entry["temporal_stability_gate"],
                            full_window_stability_gate=stability_entry[
                                "stability_gate"
                            ],
                            complete_link_gate=source_entry[
                                "complete_link_gate"
                            ],
                            preregistration=source_entry[
                                "source_preregistration"
                            ],
                            correlation_matrix=temporal_binding[
                                "correlation_matrix"
                            ],
                            selection_cells=temporal_binding[
                                "selection_cells"
                            ],
                            strategy_id=identity[0],
                            variant_id=identity[1],
                            lane=identity[2],
                        )
                    )
                    gate_verification = (
                        verify_strategy_correlation_cluster_temporal_date_grid_gate(
                            gate,
                            source_uncertainty_audit=temporal_binding[
                                "source_uncertainty_audit"
                            ],
                            source_temporal_stability_gate=report_entry[
                                "temporal_stability_gate"
                            ],
                            full_window_stability_gate=stability_entry[
                                "stability_gate"
                            ],
                            complete_link_gate=source_entry[
                                "complete_link_gate"
                            ],
                            preregistration=source_entry[
                                "source_preregistration"
                            ],
                            correlation_matrix=temporal_binding[
                                "correlation_matrix"
                            ],
                            selection_cells=temporal_binding[
                                "selection_cells"
                            ],
                            strategy_id=identity[0],
                            variant_id=identity[1],
                            lane=identity[2],
                        )
                    )
                except (
                    ArithmeticError,
                    KeyError,
                    MemoryError,
                    RecursionError,
                    TypeError,
                    ValueError,
                ):
                    expected_gate = {}
                    gate_verification = {
                        "status": "BLOCK",
                        "decision_status": "BLOCK",
                    }
                if (
                    gate_verification.get("status") != "PASS"
                    or not strict_json_contract_equal(gate, expected_gate)
                ):
                    blockers.append(
                        "temporal_date_grid_gate_invalid:"
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
                        "temporal_date_grid_gate": gate,
                        "temporal_date_grid_gate_hash": gate_hash,
                    }
                )

    decision = "BLOCK"
    decision_blockers: list[str] = []
    if not blockers and base_indexes is not None:
        order, _, _, _ = base_indexes
        if base_verification.get("decision") != "PASS":
            decision_blockers.append("base_report21_decision_blocked")
        decision_blockers.extend(
            "temporal_date_grid_gate_blocked:" + ":".join(identity)
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
            "source_base_report_hash": expected_base_report_hash,
            "base_report21_extension": report21,
            "base_report21_extension_hash": expected_report21_extension_hash,
            "registry_bindings_required": True,
            "stability_bindings_required": True,
            "temporal_stability_bindings_required": True,
            "temporal_date_grid_gate_required": True,
            "external_temporal_date_grid_bindings_required": True,
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
            expected = seal_strict_canonical_document(
                expected,
                "extension_hash",
            )
        except (TypeError, ValueError):
            blockers.append("temporal_date_grid_extension_contract_invalid")
        else:
            if not strict_json_contract_equal(document, expected):
                blockers.append("temporal_date_grid_extension_contract_invalid")

    return _verification_result(
        blockers,
        decision=decision,
        date_grid_gate_count=len(normalized_entries),
        date_grid_gate_pass_count=sum(
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
    "TEMPORAL_DATE_GRID_GATE_SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "verify_strategy_correlation_cluster_temporal_date_grid_report_extension",
]
