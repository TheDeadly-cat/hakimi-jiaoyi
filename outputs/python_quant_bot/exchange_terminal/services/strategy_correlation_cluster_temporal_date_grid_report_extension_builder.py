"""Deterministic in-memory builder for verifier-only report22 evidence."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid import (
    evaluate_strategy_correlation_cluster_temporal_date_grid_gate,
    verify_strategy_correlation_cluster_temporal_date_grid_gate,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_date_grid_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_temporal_date_grid_report_extension,
)
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_consumer import (
    verify_strategy_correlation_cluster_temporal_stability_report_extension,
)


INPUT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-extension-builder-input-v1"
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
    "expected_temporal_date_grid_gate_hash",
}
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def _identity(value: Any) -> tuple[str, str, str]:
    if type(value) is not dict:
        raise ValueError("temporal_date_grid_builder_identity_contract_invalid")
    identity = tuple(
        value.get(field) for field in ("strategy_id", "variant_id", "lane")
    )
    if not all(
        type(part) is str and part and part == part.strip()
        for part in identity
    ):
        raise ValueError("temporal_date_grid_builder_identity_invalid")
    return identity  # type: ignore[return-value]


def _clean_hash(value: Any, *, field: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{field}_invalid")
    return value


def _normalize_inputs(
    values: Any,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    if type(values) is not list or not values:
        raise ValueError("temporal_date_grid_builder_inputs_invalid")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        if type(value) is not dict or set(value) != _INPUT_FIELDS:
            raise ValueError("temporal_date_grid_builder_input_contract_invalid")
        if value.get("schema_version") != INPUT_SCHEMA_VERSION:
            raise ValueError("temporal_date_grid_builder_input_schema_invalid")
        identity = _identity(value)
        if identity in result:
            raise ValueError("temporal_date_grid_builder_identity_duplicate")
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
        _clean_hash(
            value.get("expected_temporal_date_grid_gate_hash"),
            field="expected_temporal_date_grid_gate_hash",
        )
        result[identity] = value
    return result


def _temporal_binding(value: dict[str, Any]) -> dict[str, Any]:
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


def _date_grid_binding(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy_id": value["strategy_id"],
        "variant_id": value["variant_id"],
        "lane": value["lane"],
        "expected_temporal_date_grid_gate_hash": value[
            "expected_temporal_date_grid_gate_hash"
        ],
    }


def _entry_map(
    values: Any,
    *,
    required_mapping_fields: tuple[str, ...],
) -> tuple[
    list[tuple[str, str, str]],
    dict[tuple[str, str, str], dict[str, Any]],
]:
    if type(values) is not list or not values:
        raise ValueError("temporal_date_grid_builder_entries_invalid")
    order: list[tuple[str, str, str]] = []
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        identity = _identity(value)
        if identity in result or any(
            type(value.get(field)) is not dict for field in required_mapping_fields
        ):
            raise ValueError("temporal_date_grid_builder_entry_invalid")
        order.append(identity)
        result[identity] = value
    return order, result


def build_strategy_correlation_cluster_temporal_date_grid_report_extension(
    base_report21_extension: Any,
    *,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_report21_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    temporal_date_grid_inputs: Any,
) -> dict[str, Any]:
    """Build report22 without persistence, activation, or source invention."""

    if type(base_report21_extension) is not dict:
        raise ValueError("base_report21_extension_invalid")
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
    report21_hash = _clean_hash(
        expected_report21_extension_hash,
        field="expected_report21_extension_hash",
    )
    if base_report21_extension.get("extension_hash") != report21_hash:
        raise ValueError("report21_extension_hash_mismatch")

    input_map = _normalize_inputs(temporal_date_grid_inputs)
    temporal_bindings = [
        _temporal_binding(input_map[identity])
        for identity in sorted(input_map)
    ]
    date_grid_bindings = [
        _date_grid_binding(input_map[identity])
        for identity in sorted(input_map)
    ]
    registry_bindings = deepcopy(expected_registry_bindings)
    stability_bindings = deepcopy(expected_stability_bindings)
    base_verification = (
        verify_strategy_correlation_cluster_temporal_stability_report_extension(
            base_report21_extension,
            expected_base_report_hash=base_hash,
            expected_global_independence_extension_hash=global_hash,
            expected_cluster_stability_extension_hash=stability_hash,
            expected_registry_bindings=registry_bindings,
            expected_stability_bindings=stability_bindings,
            expected_temporal_stability_bindings=temporal_bindings,
        )
    )
    if base_verification.get("status") != "PASS":
        raise ValueError("base_report21_extension_invalid")

    report_order, report_entries = _entry_map(
        base_report21_extension.get("entries"),
        required_mapping_fields=("temporal_stability_gate",),
    )
    report20 = base_report21_extension.get("base_cluster_stability_extension")
    if type(report20) is not dict:
        raise ValueError("base_report20_extension_invalid")
    _, stability_entries = _entry_map(
        report20.get("entries"),
        required_mapping_fields=("stability_gate",),
    )
    report19 = report20.get("base_global_independence_extension")
    if type(report19) is not dict:
        raise ValueError("base_report19_extension_invalid")
    _, source_entries = _entry_map(
        report19.get("entries"),
        required_mapping_fields=("source_preregistration", "complete_link_gate"),
    )
    if (
        set(report_entries) != set(stability_entries)
        or set(report_entries) != set(source_entries)
        or set(report_entries) != set(input_map)
    ):
        raise ValueError("temporal_date_grid_input_identity_binding_invalid")

    entries: list[dict[str, Any]] = []
    decision_blockers: list[str] = []
    if base_verification.get("decision") != "PASS":
        decision_blockers.append("base_report21_decision_blocked")
    for identity in report_order:
        report_entry = report_entries[identity]
        stability_entry = stability_entries[identity]
        source_entry = source_entries[identity]
        source_input = input_map[identity]
        if (
            report_entry["temporal_stability_gate"].get("gate_hash")
            != source_input["expected_temporal_stability_gate_hash"]
        ):
            raise ValueError("temporal_stability_expected_gate_hash_mismatch")
        try:
            gate = evaluate_strategy_correlation_cluster_temporal_date_grid_gate(
                deepcopy(source_input["source_uncertainty_audit"]),
                deepcopy(report_entry["temporal_stability_gate"]),
                full_window_stability_gate=deepcopy(
                    stability_entry["stability_gate"]
                ),
                complete_link_gate=deepcopy(
                    source_entry["complete_link_gate"]
                ),
                preregistration=deepcopy(
                    source_entry["source_preregistration"]
                ),
                correlation_matrix=deepcopy(
                    source_input["correlation_matrix"]
                ),
                selection_cells=deepcopy(source_input["selection_cells"]),
                strategy_id=identity[0],
                variant_id=identity[1],
                lane=identity[2],
            )
            gate_verification = (
                verify_strategy_correlation_cluster_temporal_date_grid_gate(
                    gate,
                    source_uncertainty_audit=source_input[
                        "source_uncertainty_audit"
                    ],
                    source_temporal_stability_gate=report_entry[
                        "temporal_stability_gate"
                    ],
                    full_window_stability_gate=stability_entry[
                        "stability_gate"
                    ],
                    complete_link_gate=source_entry["complete_link_gate"],
                    preregistration=source_entry["source_preregistration"],
                    correlation_matrix=source_input["correlation_matrix"],
                    selection_cells=source_input["selection_cells"],
                    strategy_id=identity[0],
                    variant_id=identity[1],
                    lane=identity[2],
                )
            )
        except (MemoryError, RecursionError):
            raise
        except (ArithmeticError, KeyError, TypeError, ValueError) as exc:
            raise ValueError("temporal_date_grid_gate_rebuild_invalid") from exc
        if gate_verification.get("status") != "PASS":
            raise ValueError("temporal_date_grid_gate_invalid")
        if (
            gate.get("gate_hash")
            != source_input["expected_temporal_date_grid_gate_hash"]
        ):
            raise ValueError("temporal_date_grid_expected_gate_hash_mismatch")
        if gate_verification.get("decision_status") != "PASS":
            decision_blockers.append(
                "temporal_date_grid_gate_blocked:" + ":".join(identity)
            )
        entries.append(
            {
                "strategy_id": identity[0],
                "variant_id": identity[1],
                "lane": identity[2],
                "temporal_date_grid_gate": gate,
                "temporal_date_grid_gate_hash": gate["gate_hash"],
            }
        )

    document = seal_strict_canonical_document(
        {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "source_base_report_hash": base_hash,
            "base_report21_extension": deepcopy(base_report21_extension),
            "base_report21_extension_hash": report21_hash,
            "registry_bindings_required": True,
            "stability_bindings_required": True,
            "temporal_stability_bindings_required": True,
            "temporal_date_grid_gate_required": True,
            "external_temporal_date_grid_bindings_required": True,
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
        verify_strategy_correlation_cluster_temporal_date_grid_report_extension(
            document,
            expected_base_report_hash=base_hash,
            expected_global_independence_extension_hash=global_hash,
            expected_cluster_stability_extension_hash=stability_hash,
            expected_report21_extension_hash=report21_hash,
            expected_registry_bindings=registry_bindings,
            expected_stability_bindings=stability_bindings,
            expected_temporal_stability_bindings=temporal_bindings,
            expected_temporal_date_grid_bindings=date_grid_bindings,
        )
    )
    if self_verification.get("status") != "PASS":
        raise ValueError("temporal_date_grid_report22_self_verification_failed")
    return document


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_temporal_date_grid_report_extension",
]
