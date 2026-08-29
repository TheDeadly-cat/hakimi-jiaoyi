"""Deterministic in-memory builder for a verified report17 extension."""

from __future__ import annotations

from typing import Any

try:
    from services.strategy_correlation_cluster_complete_link import (
        evaluate_correlation_cluster_gate_v2,
    )
    from services.strategy_correlation_complete_link_report_consumer import (
        BASE_REPORT_SCHEMA_VERSION,
        EXTENSION_SCHEMA_VERSION,
        LANES,
        TARGET_PROTOCOL_SCHEMA_VERSION,
        TARGET_REPORT_SCHEMA_VERSION,
        verify_strategy_correlation_complete_link_report_extension,
    )
    from services.strategy_correlation_multiplicity_report import (
        verify_strategy_correlation_multiplicity_report_evidence,
    )
    from services.strict_canonical_json_hash import (
        seal_strict_canonical_document,
    )
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
        evaluate_correlation_cluster_gate_v2,
    )
    from exchange_terminal.services.strategy_correlation_complete_link_report_consumer import (
        BASE_REPORT_SCHEMA_VERSION,
        EXTENSION_SCHEMA_VERSION,
        LANES,
        TARGET_PROTOCOL_SCHEMA_VERSION,
        TARGET_REPORT_SCHEMA_VERSION,
        verify_strategy_correlation_complete_link_report_extension,
    )
    from exchange_terminal.services.strategy_correlation_multiplicity_report import (
        verify_strategy_correlation_multiplicity_report_evidence,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        seal_strict_canonical_document,
    )


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{field}_invalid")
    return value


def _sha256(value: Any, *, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field}_invalid")
    return value


def build_strategy_correlation_complete_link_report_extension(
    source_evidence: Any,
    *,
    source_protocol: Any,
) -> dict[str, Any]:
    evidence = _mapping(source_evidence, field="source_evidence")
    protocol = _mapping(source_protocol, field="source_protocol")
    try:
        source_verification = (
            verify_strategy_correlation_multiplicity_report_evidence(
                evidence,
                protocol=protocol,
            )
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("source_evidence_verification_failed") from exc
    if source_verification.get("status") != "PASS":
        raise ValueError("source_evidence_verification_failed")

    base_report_hash = _sha256(
        evidence.get("evidence_hash"),
        field="source_evidence_hash",
    )
    replayed_gate = _mapping(
        evidence.get("replayed_gate"),
        field="source_replayed_gate",
    )
    matrix_replay = _mapping(
        replayed_gate.get("matrix_replay"),
        field="source_matrix_replay",
    )
    preregistration = _mapping(
        matrix_replay.get("preregistration"),
        field="source_preregistration",
    )
    correlation_matrix = _mapping(
        matrix_replay.get("correlation_matrix"),
        field="source_correlation_matrix",
    )
    selection_cells = replayed_gate.get("selection_cells")
    if type(selection_cells) is not list or not selection_cells:
        raise ValueError("source_selection_cells_invalid")

    strategy_id = replayed_gate.get("strategy_id")
    variant_id = replayed_gate.get("variant_id")
    lane = replayed_gate.get("lane")
    if (
        type(strategy_id) is not str
        or not strategy_id
        or strategy_id != strategy_id.strip()
        or type(variant_id) is not str
        or not variant_id
        or variant_id != variant_id.strip()
        or lane not in LANES
    ):
        raise ValueError("source_identity_invalid")

    try:
        gate = evaluate_correlation_cluster_gate_v2(
            preregistration,
            correlation_matrix,
            selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("complete_link_gate_build_failed") from exc
    gate_status = gate.get("status") if type(gate) is dict else None
    if gate_status not in {"PASS", "BLOCK"}:
        raise ValueError("complete_link_gate_build_failed")

    label = ":".join((strategy_id, variant_id, lane))
    decision_blockers = (
        []
        if gate_status == "PASS"
        else [f"complete_link_gate_blocked:{label}"]
    )
    extension = {
        "schema_version": EXTENSION_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "base_report_hash": base_report_hash,
        "entries": [
            {
                "strategy_id": strategy_id,
                "variant_id": variant_id,
                "lane": lane,
                "preregistration": preregistration,
                "correlation_matrix": correlation_matrix,
                "selection_cells": selection_cells,
                "gate_v2": gate,
            }
        ],
        "decision": "PASS" if not decision_blockers else "BLOCK",
        "decision_blockers": decision_blockers,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    try:
        extension = seal_strict_canonical_document(extension, "extension_hash")
        verification = verify_strategy_correlation_complete_link_report_extension(
            extension,
            expected_base_report_hash=base_report_hash,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("complete_link_extension_self_verification_failed") from exc
    if (
        verification.get("status") != "PASS"
        or verification.get("decision") != extension["decision"]
    ):
        raise ValueError("complete_link_extension_self_verification_failed")
    return extension


__all__ = ["build_strategy_correlation_complete_link_report_extension"]
