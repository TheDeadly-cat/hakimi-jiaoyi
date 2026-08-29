from __future__ import annotations

import re
from typing import Any

try:
    from services.strict_canonical_json_hash import strict_json_contract_equal
except ModuleNotFoundError:
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_json_contract_equal,
    )

try:
    from services.strategy_correlation_cluster_complete_link import (
        evaluate_correlation_cluster_gate_v2,
    )
    from services.strict_canonical_json_hash import strict_canonical_hash
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
        evaluate_correlation_cluster_gate_v2,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_canonical_hash,
    )


EXTENSION_SCHEMA_VERSION = "strategy-research-complete-link-extension-v1"
VERIFICATION_SCHEMA_VERSION = (
    "strategy-research-complete-link-extension-verification-v1"
)
BASE_REPORT_SCHEMA_VERSION = 16
TARGET_REPORT_SCHEMA_VERSION = 17
TARGET_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v6"
LANES = frozenset({"RAW_EXCESS", "RISK_ADJUSTED"})

_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}
_DOCUMENT_FIELDS = frozenset(
    {
        "schema_version",
        "base_report_schema_version",
        "target_report_schema_version",
        "target_protocol_schema_version",
        "base_report_hash",
        "entries",
        "decision",
        "decision_blockers",
        "writer_available",
        "current_admission_allowed",
        "current_writer_activation_allowed",
        "permissions",
        "extension_hash",
    }
)
_ENTRY_FIELDS = frozenset(
    {
        "strategy_id",
        "variant_id",
        "lane",
        "preregistration",
        "correlation_matrix",
        "selection_cells",
        "gate_v2",
    }
)


def _sha256(value: Any) -> str:
    return strict_canonical_hash(value)


def _seal(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "extension_hash": _sha256(payload)}


def _valid_hash(value: Any) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _identity(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError("complete_link_extension_identity_invalid")
    return value


def _verification(
    blockers: list[str],
    *,
    decision: str = "UNKNOWN",
    base_report_hash: str = "",
) -> dict[str, Any]:
    unique = sorted(set(blockers))
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not unique else "BLOCK",
        "decision": decision if not unique else "UNKNOWN",
        "blockers": unique,
        "base_report_hash": base_report_hash if not unique else "",
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def verify_strategy_correlation_complete_link_report_extension(
    document: Any,
    *,
    expected_base_report_hash: str,
) -> dict[str, Any]:
    if not _valid_hash(expected_base_report_hash):
        return _verification(["expected_base_report_hash_invalid"])
    if type(document) is not dict or set(document) != _DOCUMENT_FIELDS:
        return _verification(["complete_link_report_extension_contract_invalid"])
    if document.get("base_report_hash") != expected_base_report_hash:
        return _verification(["complete_link_report_base_hash_mismatch"])
    entries = document.get("entries")
    if type(entries) is not list or not entries:
        return _verification(["complete_link_report_entries_invalid"])

    expected_entries: list[dict[str, Any]] = []
    identities: list[tuple[str, str, str]] = []
    try:
        for entry in entries:
            if type(entry) is not dict or set(entry) != _ENTRY_FIELDS:
                raise ValueError("complete_link_report_entry_contract_invalid")
            strategy_id = _identity(entry.get("strategy_id"))
            variant_id = _identity(entry.get("variant_id"))
            lane = _identity(entry.get("lane"))
            if lane not in LANES:
                raise ValueError("complete_link_report_entry_lane_invalid")
            if type(entry.get("preregistration")) is not dict:
                raise ValueError("complete_link_report_entry_source_invalid")
            if type(entry.get("correlation_matrix")) is not dict:
                raise ValueError("complete_link_report_entry_source_invalid")
            if type(entry.get("selection_cells")) is not list:
                raise ValueError("complete_link_report_entry_source_invalid")
            identity = (strategy_id, variant_id, lane)
            identities.append(identity)
            expected_entries.append(
                {
                    "strategy_id": strategy_id,
                    "variant_id": variant_id,
                    "lane": lane,
                    "preregistration": entry["preregistration"],
                    "correlation_matrix": entry["correlation_matrix"],
                    "selection_cells": entry["selection_cells"],
                    "gate_v2": evaluate_correlation_cluster_gate_v2(
                        entry["preregistration"],
                        entry["correlation_matrix"],
                        entry["selection_cells"],
                        strategy_id=strategy_id,
                        variant_id=variant_id,
                        lane=lane,
                    ),
                }
            )
    except (KeyError, TypeError, ValueError) as exc:
        blocker = str(exc) if str(exc).startswith("complete_link_report_") else (
            "complete_link_report_entry_source_invalid"
        )
        return _verification([blocker])

    if len(set(identities)) != len(identities):
        return _verification(["complete_link_report_entry_identity_duplicate"])
    if identities != sorted(identities):
        return _verification(["complete_link_report_entry_order_invalid"])

    decision_blockers = [
        "complete_link_gate_blocked:" + ":".join(identity)
        for identity, entry in zip(identities, expected_entries, strict=True)
        if entry["gate_v2"]["status"] != "PASS"
    ]
    decision = "BLOCK" if decision_blockers else "PASS"
    expected = _seal(
        {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "base_report_hash": expected_base_report_hash,
            "entries": expected_entries,
            "decision": decision,
            "decision_blockers": decision_blockers,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": dict(_PERMISSIONS),
        }
    )
    if type(document) is not dict or not strict_json_contract_equal(
        document,
        expected,
    ):
        return _verification(["complete_link_report_extension_contract_invalid"])
    return _verification(
        [],
        decision=decision,
        base_report_hash=expected_base_report_hash,
    )
