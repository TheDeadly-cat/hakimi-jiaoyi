"""Consumer-only verifier for report18 preregistered strata evidence."""

from __future__ import annotations

import re
from typing import Any

try:
    from services.strategy_correlation_complete_link_report_consumer import (
        EXTENSION_SCHEMA_VERSION as COMPLETE_LINK_EXTENSION_SCHEMA,
        verify_strategy_correlation_complete_link_report_extension,
    )
    from services.strategy_correlation_preregistered_strata import (
        verify_strategy_correlation_strata_gate,
        verify_strategy_correlation_strata_preregistration,
    )
    from services.strategy_correlation_strata_registry import (
        verify_strategy_correlation_strata_registry_asset,
        verify_strategy_correlation_strata_registry_binding,
    )
    from services.strict_canonical_json_hash import (
        strict_canonical_hash,
        strict_json_contract_equal,
    )
    from services.strict_research_authority import (
        strict_research_authority_invalid,
    )
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_complete_link_report_consumer import (
        EXTENSION_SCHEMA_VERSION as COMPLETE_LINK_EXTENSION_SCHEMA,
        verify_strategy_correlation_complete_link_report_extension,
    )
    from exchange_terminal.services.strategy_correlation_preregistered_strata import (
        verify_strategy_correlation_strata_gate,
        verify_strategy_correlation_strata_preregistration,
    )
    from exchange_terminal.services.strategy_correlation_strata_registry import (
        verify_strategy_correlation_strata_registry_asset,
        verify_strategy_correlation_strata_registry_binding,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_canonical_hash,
        strict_json_contract_equal,
    )
    from exchange_terminal.services.strict_research_authority import (
        strict_research_authority_invalid,
    )


EXTENSION_SCHEMA_VERSION = "strategy-research-preregistered-strata-extension-v1"
VERIFICATION_SCHEMA_VERSION = (
    "strategy-research-preregistered-strata-extension-verification-v1"
)
BASE_REPORT_SCHEMA_VERSION = 17
TARGET_REPORT_SCHEMA_VERSION = 18
BASE_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v6"
TARGET_PROTOCOL_SCHEMA_VERSION = "strategy-matrix-protocol-v7"
LANES = frozenset({"RAW_EXCESS", "RISK_ADJUSTED"})
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}
_DOCUMENT_FIELDS = frozenset(
    {
        "schema_version",
        "base_report_schema_version",
        "target_report_schema_version",
        "base_protocol_schema_version",
        "target_protocol_schema_version",
        "base_report_hash",
        "base_complete_link_extension",
        "base_complete_link_extension_hash",
        "entries",
        "decision",
        "decision_blockers",
        "registry_binding_required",
        "consumer_only",
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
        "source_preregistration",
        "strata_registration",
        "complete_link_gate",
        "strata_gate",
        "registry_asset",
        "registry_binding",
    }
)
_EXPECTED_BINDING_FIELDS = frozenset(
    {
        "strategy_id",
        "variant_id",
        "lane",
        "selection_cutoff_date",
        "expected_registry_asset_hash",
        "expected_classification_source_hash",
    }
)


def _clean_hash(value: Any, *, field: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field}_invalid")
    return value


def _identity(value: Any) -> tuple[str, str, str]:
    if type(value) is not dict:
        raise ValueError("entry_contract_invalid")
    strategy_id = value.get("strategy_id")
    variant_id = value.get("variant_id")
    lane = value.get("lane")
    if (
        type(strategy_id) is not str
        or not strategy_id
        or strategy_id != strategy_id.strip()
        or type(variant_id) is not str
        or not variant_id
        or variant_id != variant_id.strip()
        or lane not in LANES
    ):
        raise ValueError("entry_identity_invalid")
    return strategy_id, variant_id, lane


def _identity_label(identity: tuple[str, str, str]) -> str:
    return ":".join(identity)


def _hash_without(document: dict[str, Any], hash_field: str) -> str:
    return strict_canonical_hash(
        {key: value for key, value in document.items() if key != hash_field}
    )


def _expected_binding_map(
    values: Any,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    if type(values) is not list or not values:
        raise ValueError("expected_registry_bindings_invalid")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        if type(value) is not dict or set(value) != _EXPECTED_BINDING_FIELDS:
            raise ValueError("expected_registry_binding_contract_invalid")
        identity = _identity(value)
        if identity in result:
            raise ValueError("expected_registry_binding_duplicate")
        _clean_hash(
            value.get("expected_registry_asset_hash"),
            field="expected_registry_asset_hash",
        )
        _clean_hash(
            value.get("expected_classification_source_hash"),
            field="expected_classification_source_hash",
        )
        cutoff = value.get("selection_cutoff_date")
        if type(cutoff) is not str or not cutoff:
            raise ValueError("selection_cutoff_date_invalid")
        result[identity] = value
    return result


def verify_strategy_correlation_strata_report_extension(
    document: Any,
    *,
    expected_base_report_hash: Any,
    expected_registry_bindings: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        normalized_base_hash = _clean_hash(
            expected_base_report_hash,
            field="expected_base_report_hash",
        )
    except ValueError:
        normalized_base_hash = None
        blockers.append("expected_base_report_hash_invalid")
    try:
        expected_bindings = _expected_binding_map(
            expected_registry_bindings
        )
    except (TypeError, ValueError):
        expected_bindings = {}
        blockers.append("expected_registry_bindings_invalid")

    if type(document) is not dict or set(document) != _DOCUMENT_FIELDS:
        return {
            "schema_version": VERIFICATION_SCHEMA_VERSION,
            "status": "BLOCK",
            "blockers": sorted(
                set(blockers + ["strata_report_extension_contract_invalid"])
            ),
            "decision": "UNKNOWN",
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "registry_binding_required": True,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": dict(_PERMISSIONS),
        }
    if strict_research_authority_invalid(document):
        blockers.append("strata_report_extension_authority_invalid")
    try:
        if document.get("extension_hash") != _hash_without(
            document,
            "extension_hash",
        ):
            blockers.append("strata_report_extension_hash_invalid")
    except (TypeError, ValueError):
        blockers.append("strata_report_extension_hash_invalid")

    fixed_values = {
        "schema_version": EXTENSION_SCHEMA_VERSION,
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "registry_binding_required": True,
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": _PERMISSIONS,
    }
    if any(
        not strict_json_contract_equal(document.get(key), value)
        for key, value in fixed_values.items()
    ):
        blockers.append("strata_report_extension_fixed_contract_invalid")
    if (
        normalized_base_hash is None
        or document.get("base_report_hash") != normalized_base_hash
    ):
        blockers.append("strata_report_base_hash_mismatch")

    base_extension = document.get("base_complete_link_extension")
    base_entries: dict[tuple[str, str, str], dict[str, Any]] = {}
    base_decision = "BLOCK"
    if (
        type(base_extension) is not dict
        or base_extension.get("schema_version")
        != COMPLETE_LINK_EXTENSION_SCHEMA
    ):
        blockers.append("base_complete_link_extension_invalid")
    elif normalized_base_hash is not None:
        base_verification = (
            verify_strategy_correlation_complete_link_report_extension(
                base_extension,
                expected_base_report_hash=normalized_base_hash,
            )
        )
        if base_verification.get("status") != "PASS":
            blockers.append("base_complete_link_extension_invalid")
        else:
            base_decision = base_extension.get("decision")
            try:
                for entry in base_extension.get("entries", []):
                    identity = _identity(entry)
                    if identity in base_entries:
                        raise ValueError("duplicate")
                    base_entries[identity] = entry
            except (TypeError, ValueError):
                blockers.append("base_complete_link_entries_invalid")
                base_entries = {}
    if (
        type(base_extension) is not dict
        or document.get("base_complete_link_extension_hash")
        != base_extension.get("extension_hash")
    ):
        blockers.append("base_complete_link_extension_hash_mismatch")

    entries = document.get("entries")
    entry_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    identities_in_order: list[tuple[str, str, str]] = []
    if type(entries) is not list or not entries:
        blockers.append("strata_report_entries_invalid")
    else:
        try:
            for entry in entries:
                if type(entry) is not dict or set(entry) != _ENTRY_FIELDS:
                    raise ValueError("contract")
                identity = _identity(entry)
                if identity in entry_map:
                    raise ValueError("duplicate")
                entry_map[identity] = entry
                identities_in_order.append(identity)
        except (TypeError, ValueError):
            blockers.append("strata_report_entries_invalid")
            entry_map = {}
            identities_in_order = []
    if identities_in_order and identities_in_order != sorted(
        identities_in_order
    ):
        blockers.append("strata_report_entry_order_invalid")
    if (
        set(entry_map) != set(base_entries)
        or set(entry_map) != set(expected_bindings)
    ):
        blockers.append("strata_report_entry_identity_binding_invalid")

    decision_blockers: list[str] = []
    if base_decision != "PASS":
        decision_blockers.append("complete_link_extension_blocked")
    for identity in sorted(entry_map):
        entry = entry_map[identity]
        base_entry = base_entries.get(identity)
        expected_binding = expected_bindings.get(identity)
        label = _identity_label(identity)
        if base_entry is None or expected_binding is None:
            continue
        if (
            entry.get("source_preregistration")
            != base_entry.get("preregistration")
            or entry.get("complete_link_gate")
            != base_entry.get("gate_v2")
        ):
            blockers.append(f"strata_report_source_binding_invalid:{label}")
            continue
        source_preregistration = entry["source_preregistration"]
        registration = entry["strata_registration"]
        complete_link_gate = entry["complete_link_gate"]
        strata_gate = entry["strata_gate"]
        registry_asset = entry["registry_asset"]
        registry_binding = entry["registry_binding"]

        registration_verification = (
            verify_strategy_correlation_strata_preregistration(
                registration,
                source_preregistration=source_preregistration,
            )
        )
        if registration_verification.get("status") != "PASS":
            blockers.append(
                f"strata_report_registration_invalid:{label}"
            )
        gate_verification = verify_strategy_correlation_strata_gate(
            strata_gate,
            registration=registration,
            complete_link_gate=complete_link_gate,
            source_preregistration=source_preregistration,
        )
        if gate_verification.get("status") != "PASS":
            blockers.append(f"strata_report_gate_invalid:{label}")
        asset_verification = (
            verify_strategy_correlation_strata_registry_asset(
                registry_asset,
                source_preregistration=source_preregistration,
            )
        )
        if asset_verification.get("status") != "PASS":
            blockers.append(
                f"strata_report_registry_asset_invalid:{label}"
            )
        binding_verification = (
            verify_strategy_correlation_strata_registry_binding(
                registry_binding,
                registry_asset=registry_asset,
                registration=registration,
                source_preregistration=source_preregistration,
                selection_cutoff_date=expected_binding[
                    "selection_cutoff_date"
                ],
                expected_registry_asset_hash=expected_binding[
                    "expected_registry_asset_hash"
                ],
                expected_classification_source_hash=expected_binding[
                    "expected_classification_source_hash"
                ],
            )
        )
        if binding_verification.get("status") != "PASS":
            blockers.append(
                f"strata_report_registry_binding_invalid:{label}"
            )
        if type(strata_gate) is dict and strata_gate.get("status") != "PASS":
            decision_blockers.append(f"strata_gate_blocked:{label}")
        if (
            type(registry_binding) is not dict
            or registry_binding.get("status") != "BOUND"
        ):
            decision_blockers.append(
                f"strata_registry_binding_blocked:{label}"
            )

    expected_decision = "PASS" if not decision_blockers else "BLOCK"
    if document.get("decision") != expected_decision:
        blockers.append("strata_report_decision_invalid")
    if document.get("decision_blockers") != decision_blockers:
        blockers.append("strata_report_decision_blockers_invalid")

    blockers = sorted(set(blockers))
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "decision": expected_decision if not blockers else "UNKNOWN",
        "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "registry_binding_required": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
