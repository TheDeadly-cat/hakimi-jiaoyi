"""Deterministic in-memory builder for verified report21 evidence."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from exchange_terminal.services.strategy_correlation_cluster_stability_report_consumer import (
    verify_strategy_correlation_cluster_stability_report_extension,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability import (
    evaluate_strategy_correlation_cluster_temporal_stability_gate,
    verify_strategy_correlation_cluster_temporal_stability_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_stability_report_extension,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


INPUT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-stability-extension-builder-input-v1"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_INPUT_FIELDS = {
    "schema_version",
    "strategy_id",
    "variant_id",
    "lane",
    "source_uncertainty_audit",
    "correlation_matrix",
    "selection_cells",
    "expected_temporal_stability_gate_hash",
}
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def _identity(value: Any) -> tuple[str, str, str]:
    if type(value) is not dict:
        raise ValueError("temporal_stability_builder_identity_contract_invalid")
    identity = tuple(
        value.get(field) for field in ("strategy_id", "variant_id", "lane")
    )
    if not all(
        type(part) is str
        and part
        and part == part.strip()
        for part in identity
    ):
        raise ValueError("temporal_stability_builder_identity_invalid")
    return identity  # type: ignore[return-value]


def _clean_hash(value: Any, *, field: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field}_invalid")
    return value


def _normalize_inputs(
    values: Any,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    if type(values) is not list or not values:
        raise ValueError("temporal_stability_builder_inputs_invalid")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        if type(value) is not dict or set(value) != _INPUT_FIELDS:
            raise ValueError("temporal_stability_builder_input_contract_invalid")
        if value.get("schema_version") != INPUT_SCHEMA_VERSION:
            raise ValueError("temporal_stability_builder_input_schema_invalid")
        identity = _identity(value)
        if identity in result:
            raise ValueError("temporal_stability_builder_identity_duplicate")
        if type(value.get("source_uncertainty_audit")) is not dict:
            raise ValueError("source_uncertainty_audit_invalid")
        if type(value.get("correlation_matrix")) is not dict:
            raise ValueError("correlation_matrix_invalid")
        if type(value.get("selection_cells")) is not list:
            raise ValueError("selection_cells_invalid")
        _clean_hash(
            value.get("expected_temporal_stability_gate_hash"),
            field="expected_temporal_stability_gate_hash",
        )
        result[identity] = value
    return result


def _expected_binding(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy_id": value["strategy_id"],
        "variant_id": value["variant_id"],
        "lane": value["lane"],
        "source_uncertainty_audit": deepcopy(
            value["source_uncertainty_audit"]
        ),
        "correlation_matrix": deepcopy(value["correlation_matrix"]),
        "selection_cells": deepcopy(value["selection_cells"]),
        "expected_temporal_stability_gate_hash": value[
            "expected_temporal_stability_gate_hash"
        ],
    }


def build_strategy_correlation_cluster_temporal_stability_report_extension(
    base_cluster_stability_extension: Any,
    *,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    temporal_inputs: Any,
) -> dict[str, Any]:
    """Build report21 without persistence, activation, or source invention."""

    if type(base_cluster_stability_extension) is not dict:
        raise ValueError("base_cluster_stability_extension_invalid")
    if type(expected_registry_bindings) is not list:
        raise ValueError("expected_registry_bindings_invalid")
    if type(expected_stability_bindings) is not list:
        raise ValueError("expected_stability_bindings_invalid")
    base_hash = _clean_hash(
        expected_base_report_hash,
        field="expected_base_report_hash",
    )
    global_hash = _clean_hash(
        expected_global_independence_extension_hash,
        field="expected_global_independence_extension_hash",
    )
    stability_hash = _clean_hash(
        expected_cluster_stability_extension_hash,
        field="expected_cluster_stability_extension_hash",
    )
    if base_cluster_stability_extension.get("extension_hash") != stability_hash:
        raise ValueError("cluster_stability_extension_hash_mismatch")
    normalized_registry_bindings = deepcopy(expected_registry_bindings)
    normalized_stability_bindings = deepcopy(expected_stability_bindings)
    base_verification = verify_strategy_correlation_cluster_stability_report_extension(
        base_cluster_stability_extension,
        expected_base_report_hash=base_hash,
        expected_global_independence_extension_hash=global_hash,
        expected_registry_bindings=normalized_registry_bindings,
        expected_stability_bindings=normalized_stability_bindings,
    )
    if base_verification.get("status") != "PASS":
        raise ValueError("base_cluster_stability_extension_invalid")
    input_map = _normalize_inputs(temporal_inputs)

    source_extension = base_cluster_stability_extension.get(
        "base_global_independence_extension"
    )
    source_entries = (
        source_extension.get("entries")
        if type(source_extension) is dict
        else None
    )
    base_entry_values = base_cluster_stability_extension.get("entries")
    if type(base_entry_values) is not list or type(source_entries) is not list:
        raise ValueError("base_cluster_stability_entries_invalid")
    base_order: list[tuple[str, str, str]] = []
    base_entries: dict[tuple[str, str, str], dict[str, Any]] = {}
    source_entry_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for base_entry in base_entry_values:
        identity = _identity(base_entry)
        if identity in base_entries:
            raise ValueError("base_cluster_stability_entry_duplicate")
        base_order.append(identity)
        base_entries[identity] = base_entry
    for source_entry in source_entries:
        identity = _identity(source_entry)
        if identity in source_entry_map:
            raise ValueError("source_global_independence_entry_duplicate")
        source_entry_map[identity] = source_entry
    if (
        not base_entries
        or set(base_entries) != set(source_entry_map)
        or set(base_entries) != set(input_map)
    ):
        raise ValueError("temporal_stability_input_identity_binding_invalid")

    entries: list[dict[str, Any]] = []
    expected_temporal_bindings: list[dict[str, Any]] = []
    decision_blockers: list[str] = []
    if base_verification.get("decision") != "PASS":
        decision_blockers.append("base_cluster_stability_decision_blocked")
    for identity in base_order:
        base_entry = base_entries[identity]
        source_entry = source_entry_map[identity]
        source_input = input_map[identity]
        source_uncertainty_audit = deepcopy(
            source_input["source_uncertainty_audit"]
        )
        correlation_matrix = deepcopy(source_input["correlation_matrix"])
        selection_cells = deepcopy(source_input["selection_cells"])
        try:
            temporal_gate = (
                evaluate_strategy_correlation_cluster_temporal_stability_gate(
                    source_uncertainty_audit,
                    deepcopy(base_entry["stability_gate"]),
                    complete_link_gate=deepcopy(
                        source_entry["complete_link_gate"]
                    ),
                    preregistration=deepcopy(
                        source_entry["source_preregistration"]
                    ),
                    correlation_matrix=correlation_matrix,
                    selection_cells=selection_cells,
                    strategy_id=identity[0],
                    variant_id=identity[1],
                    lane=identity[2],
                )
            )
            gate_verification = (
                verify_strategy_correlation_cluster_temporal_stability_gate(
                    temporal_gate,
                    source_uncertainty_audit=source_uncertainty_audit,
                    full_window_stability_gate=base_entry[
                        "stability_gate"
                    ],
                    complete_link_gate=source_entry["complete_link_gate"],
                    preregistration=source_entry["source_preregistration"],
                    correlation_matrix=correlation_matrix,
                    selection_cells=selection_cells,
                    strategy_id=identity[0],
                    variant_id=identity[1],
                    lane=identity[2],
                )
            )
        except (MemoryError, RecursionError):
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("temporal_stability_gate_rebuild_invalid") from exc
        if gate_verification.get("status") != "PASS":
            raise ValueError("temporal_stability_gate_invalid")
        if (
            temporal_gate.get("gate_hash")
            != source_input["expected_temporal_stability_gate_hash"]
        ):
            raise ValueError("temporal_stability_expected_gate_hash_mismatch")
        if gate_verification.get("decision_status") != "PASS":
            decision_blockers.append(
                "cluster_temporal_stability_gate_blocked:"
                + ":".join(identity)
            )
        entries.append(
            {
                "strategy_id": identity[0],
                "variant_id": identity[1],
                "lane": identity[2],
                "temporal_stability_gate": temporal_gate,
                "temporal_stability_gate_hash": temporal_gate["gate_hash"],
            }
        )
        expected_temporal_bindings.append(_expected_binding(source_input))

    document = seal_strict_canonical_document(
        {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "base_report_hash": base_hash,
            "base_cluster_stability_extension": deepcopy(
                base_cluster_stability_extension
            ),
            "base_cluster_stability_extension_hash": stability_hash,
            "registry_bindings_required": True,
            "stability_bindings_required": True,
            "temporal_stability_gate_required": True,
            "external_temporal_stability_bindings_required": True,
            "entries": entries,
            "decision": "PASS" if not decision_blockers else "BLOCK",
            "decision_blockers": decision_blockers,
            "consumer_only": True,
            "requires_new_report_schema": True,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": dict(_PERMISSIONS),
        },
        "extension_hash",
    )
    self_verification = (
        verify_strategy_correlation_cluster_temporal_stability_report_extension(
            document,
            expected_base_report_hash=base_hash,
            expected_global_independence_extension_hash=global_hash,
            expected_cluster_stability_extension_hash=stability_hash,
            expected_registry_bindings=normalized_registry_bindings,
            expected_stability_bindings=normalized_stability_bindings,
            expected_temporal_stability_bindings=expected_temporal_bindings,
        )
    )
    if self_verification.get("status") != "PASS":
        raise ValueError(
            "temporal_stability_report_extension_self_verification_failed"
        )
    return document
