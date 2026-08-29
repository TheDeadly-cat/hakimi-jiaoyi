"""Verifier-only report-19 extension for cross-dimension independence evidence.

This module deliberately has no builder, persistence path, current-pointer
mutation, or trading authority.  It accepts a report-18 strata extension only
after that extension is independently verified, then rebuilds every embedded
global-independence gate from its report-18 inputs.
"""

from __future__ import annotations

import re
from typing import Any

try:
    from .strict_canonical_json_hash import (
        strict_canonical_hash,
        strict_json_contract_equal,
    )
    from .strict_research_authority import strict_research_authority_violations
    from .strategy_correlation_strata_global_independence import (
        GATE_SCHEMA_VERSION as GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION,
        verify_strategy_correlation_strata_global_independence_gate,
    )
    from .strategy_correlation_strata_report_consumer import (
        EXTENSION_SCHEMA_VERSION as STRATA_EXTENSION_SCHEMA_VERSION,
        verify_strategy_correlation_strata_report_extension,
    )
except ImportError:  # pragma: no cover - direct exchange_terminal script imports
    from services.strict_canonical_json_hash import (
        strict_canonical_hash,
        strict_json_contract_equal,
    )
    from services.strict_research_authority import strict_research_authority_violations
    from services.strategy_correlation_strata_global_independence import (
        GATE_SCHEMA_VERSION as GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION,
        verify_strategy_correlation_strata_global_independence_gate,
    )
    from services.strategy_correlation_strata_report_consumer import (
        EXTENSION_SCHEMA_VERSION as STRATA_EXTENSION_SCHEMA_VERSION,
        verify_strategy_correlation_strata_report_extension,
    )


EXTENSION_SCHEMA_VERSION = "strategy-research-global-independence-extension-v1"
VERIFICATION_SCHEMA_VERSION = (
    "strategy-research-global-independence-extension-verification-v1"
)
BASE_REPORT_SCHEMA_VERSION = 18
TARGET_REPORT_SCHEMA_VERSION = 19
BASE_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v7"
TARGET_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v8"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_ROOT_FIELDS = {
    "schema_version",
    "base_report_schema_version",
    "target_report_schema_version",
    "base_protocol_schema_version",
    "target_protocol_schema_version",
    "base_report_hash",
    "base_strata_extension",
    "base_strata_extension_hash",
    "entries",
    "decision",
    "decision_blockers",
    "registry_binding_required",
    "global_independence_required",
    "consumer_only",
    "writer_available",
    "current_admission_allowed",
    "current_writer_activation_allowed",
    "permissions",
    "extension_hash",
}
_ENTRY_FIELDS = {
    "strategy_id",
    "variant_id",
    "lane",
    "source_preregistration",
    "strata_registration",
    "complete_link_gate",
    "strata_gate",
    "global_independence_gate",
}
_IDENTITY_FIELDS = ("strategy_id", "variant_id", "lane")


def _deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _identity(value: Any) -> tuple[str, str, str] | None:
    if type(value) is not dict:
        return None
    parts = tuple(value.get(field) for field in _IDENTITY_FIELDS)
    if not all(type(part) is str and part for part in parts):
        return None
    return parts  # type: ignore[return-value]


def _verification(*, status: str, decision: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "registry_binding_required": True,
        "global_independence_required": True,
        "status": status,
        "decision": decision,
        "blockers": _deduplicate(blockers),
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def _contract_failure(blockers: list[str]) -> dict[str, Any]:
    return _verification(status="BLOCK", decision="BLOCK", blockers=blockers)


def verify_strategy_correlation_global_independence_report_extension(
    document: Any,
    *,
    expected_base_report_hash: Any,
    expected_registry_bindings: Any,
) -> dict[str, Any]:
    """Verify a consumer-supplied report-19 extension without issuing one."""

    contract_blockers: list[str] = []
    if type(document) is not dict:
        return _contract_failure(["extension_invalid"])

    if set(document) != _ROOT_FIELDS:
        contract_blockers.append("extension_fields_mismatch")
    expected_constants = {
        "schema_version": EXTENSION_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "registry_binding_required": True,
        "global_independence_required": True,
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": _PERMISSIONS,
    }
    for field, expected in expected_constants.items():
        if not strict_json_contract_equal(document.get(field), expected):
            contract_blockers.append(f"{field}_mismatch")

    if strict_research_authority_violations(document):
        contract_blockers.append("research_authority_violation")

    if type(expected_base_report_hash) is not str or not _SHA256_RE.fullmatch(
        expected_base_report_hash
    ):
        contract_blockers.append("expected_base_report_hash_invalid")
    elif document.get("base_report_hash") != expected_base_report_hash:
        contract_blockers.append("base_report_hash_mismatch")

    base_extension = document.get("base_strata_extension")
    base_verification: dict[str, Any] | None = None
    if type(base_extension) is not dict:
        contract_blockers.append("base_strata_extension_invalid")
    else:
        if base_extension.get("schema_version") != STRATA_EXTENSION_SCHEMA_VERSION:
            contract_blockers.append("base_strata_extension_schema_mismatch")
        if document.get("base_strata_extension_hash") != base_extension.get(
            "extension_hash"
        ):
            contract_blockers.append("base_strata_extension_hash_mismatch")
        if base_extension.get("base_report_hash") != document.get("base_report_hash"):
            contract_blockers.append("base_strata_report_hash_mismatch")
        try:
            base_verification = verify_strategy_correlation_strata_report_extension(
                base_extension,
                expected_base_report_hash=expected_base_report_hash,
                expected_registry_bindings=expected_registry_bindings,
            )
        except (TypeError, ValueError):
            contract_blockers.append("base_strata_extension_invalid")
        else:
            if base_verification.get("status") != "PASS":
                contract_blockers.append("base_strata_extension_invalid")

    entries = document.get("entries")
    base_entries = base_extension.get("entries") if type(base_extension) is dict else None
    if type(entries) is not list or not entries:
        contract_blockers.append("entries_invalid")
        entries = []
    if type(base_entries) is not list or not base_entries:
        contract_blockers.append("base_entries_invalid")
        base_entries = []

    base_by_identity: dict[tuple[str, str, str], dict[str, Any]] = {}
    for base_entry in base_entries:
        identity = _identity(base_entry)
        if identity is None or identity in base_by_identity:
            contract_blockers.append("base_entry_identity_invalid")
            continue
        base_by_identity[identity] = base_entry

    entry_by_identity: dict[tuple[str, str, str], dict[str, Any]] = {}
    global_statuses: dict[tuple[str, str, str], str] = {}
    for entry in entries:
        identity = _identity(entry)
        if identity is None or identity in entry_by_identity:
            contract_blockers.append("entry_identity_invalid")
            continue
        entry_by_identity[identity] = entry
        if set(entry) != _ENTRY_FIELDS:
            contract_blockers.append(
                "entry_fields_mismatch:" + ":".join(identity)
            )
        base_entry = base_by_identity.get(identity)
        if base_entry is None:
            contract_blockers.append(
                "entry_identity_mismatch:" + ":".join(identity)
            )
            continue

        source_fields = (
            "source_preregistration",
            "strata_registration",
            "complete_link_gate",
            "strata_gate",
        )
        if any(entry.get(field) != base_entry.get(field) for field in source_fields):
            contract_blockers.append(
                "entry_source_mismatch:" + ":".join(identity)
            )
            continue

        global_gate = entry.get("global_independence_gate")
        if type(global_gate) is not dict:
            contract_blockers.append(
                "global_independence_gate_missing:" + ":".join(identity)
            )
            continue
        if global_gate.get("schema_version") != GLOBAL_INDEPENDENCE_GATE_SCHEMA_VERSION:
            contract_blockers.append(
                "global_independence_gate_schema_mismatch:" + ":".join(identity)
            )
        if _identity(global_gate) != identity:
            contract_blockers.append(
                "global_independence_gate_identity_mismatch:" + ":".join(identity)
            )
        try:
            gate_verification = (
                verify_strategy_correlation_strata_global_independence_gate(
                    global_gate,
                    registration=entry.get("strata_registration"),
                    complete_link_gate=entry.get("complete_link_gate"),
                    strata_gate=entry.get("strata_gate"),
                    source_preregistration=entry.get("source_preregistration"),
                )
            )
        except (TypeError, ValueError):
            contract_blockers.append(
                "global_independence_gate_invalid:" + ":".join(identity)
            )
        else:
            if gate_verification.get("status") != "PASS":
                contract_blockers.append(
                    "global_independence_gate_invalid:" + ":".join(identity)
                )
            gate_status = global_gate.get("status")
            if gate_status not in {"PASS", "BLOCK"}:
                contract_blockers.append(
                    "global_independence_gate_status_invalid:" + ":".join(identity)
                )
            else:
                global_statuses[identity] = gate_status

    if set(entry_by_identity) != set(base_by_identity):
        contract_blockers.append("entry_identity_set_mismatch")

    if contract_blockers:
        return _contract_failure(contract_blockers)

    decision_blockers: list[str] = []
    if base_verification is None or base_verification.get("decision") != "PASS":
        decision_blockers.append("strata_extension_blocked")
    for identity in entry_by_identity:
        if global_statuses.get(identity) != "PASS":
            decision_blockers.append(
                "global_independence_gate_blocked:" + ":".join(identity)
            )
    decision = "PASS" if not decision_blockers else "BLOCK"
    if document.get("decision") != decision:
        contract_blockers.append("decision_mismatch")
    if document.get("decision_blockers") != decision_blockers:
        contract_blockers.append("decision_blockers_mismatch")

    extension_hash = document.get("extension_hash")
    if type(extension_hash) is not str or not _SHA256_RE.fullmatch(extension_hash):
        contract_blockers.append("extension_hash_invalid")
    else:
        hash_payload = dict(document)
        hash_payload.pop("extension_hash", None)
        try:
            expected_extension_hash = strict_canonical_hash(hash_payload)
        except (TypeError, ValueError):
            contract_blockers.append("extension_hash_invalid")
        else:
            if extension_hash != expected_extension_hash:
                contract_blockers.append("extension_hash_mismatch")

    if contract_blockers:
        return _contract_failure(contract_blockers)
    return _verification(status="PASS", decision=decision, blockers=decision_blockers)


__all__ = [
    "BASE_PROTOCOL_SCHEMA_VERSION",
    "BASE_REPORT_SCHEMA_VERSION",
    "EXTENSION_SCHEMA_VERSION",
    "TARGET_PROTOCOL_SCHEMA_VERSION",
    "TARGET_REPORT_SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "verify_strategy_correlation_global_independence_report_extension",
]
