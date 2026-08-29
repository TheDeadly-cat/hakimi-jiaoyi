"""Deterministic in-memory builder for verified report19 evidence."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from exchange_terminal.services.strategy_correlation_global_independence_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_global_independence_report_extension,
)
from exchange_terminal.services.strategy_correlation_strata_global_independence import (
    evaluate_strategy_correlation_strata_global_independence_gate,
    verify_strategy_correlation_strata_global_independence_gate,
)
from exchange_terminal.services.strategy_correlation_strata_report_consumer import (
    verify_strategy_correlation_strata_report_extension,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def _identity(value: Any) -> tuple[str, str, str]:
    if type(value) is not dict:
        raise ValueError("global_independence_builder_entry_invalid")
    identity = tuple(
        value.get(field) for field in ("strategy_id", "variant_id", "lane")
    )
    if not all(
        type(part) is str
        and part
        and part == part.strip()
        for part in identity
    ):
        raise ValueError("global_independence_builder_identity_invalid")
    return identity  # type: ignore[return-value]


def build_strategy_correlation_global_independence_report_extension(
    base_strata_extension: Any,
    *,
    expected_base_report_hash: Any,
    expected_registry_bindings: Any,
) -> dict[str, Any]:
    """Build report19 without persistence, activation, or new source claims."""

    if type(base_strata_extension) is not dict:
        raise ValueError("base_strata_extension_invalid")
    if type(expected_registry_bindings) is not list:
        raise ValueError("expected_registry_bindings_invalid")
    base_hash = expected_base_report_hash
    if type(base_hash) is not str or _SHA256_RE.fullmatch(base_hash) is None:
        raise ValueError("expected_base_report_hash_invalid")
    normalized_bindings = deepcopy(expected_registry_bindings)
    base_verification = verify_strategy_correlation_strata_report_extension(
        base_strata_extension,
        expected_base_report_hash=base_hash,
        expected_registry_bindings=normalized_bindings,
    )
    if base_verification.get("status") != "PASS":
        raise ValueError("base_strata_extension_invalid")

    base_entries: dict[tuple[str, str, str], dict[str, Any]] = {}
    for base_entry in base_strata_extension.get("entries", []):
        identity = _identity(base_entry)
        if identity in base_entries:
            raise ValueError("base_strata_entry_duplicate")
        base_entries[identity] = base_entry
    if not base_entries:
        raise ValueError("base_strata_entries_invalid")

    entries: list[dict[str, Any]] = []
    decision_blockers: list[str] = []
    if base_verification.get("decision") != "PASS":
        decision_blockers.append("strata_extension_blocked")
    for identity in sorted(base_entries):
        base_entry = base_entries[identity]
        source_preregistration = deepcopy(
            base_entry["source_preregistration"]
        )
        strata_registration = deepcopy(base_entry["strata_registration"])
        complete_link_gate = deepcopy(base_entry["complete_link_gate"])
        strata_gate = deepcopy(base_entry["strata_gate"])
        try:
            global_gate = (
                evaluate_strategy_correlation_strata_global_independence_gate(
                    strata_registration,
                    complete_link_gate,
                    strata_gate,
                    source_preregistration=source_preregistration,
                )
            )
            gate_verification = (
                verify_strategy_correlation_strata_global_independence_gate(
                    global_gate,
                    registration=strata_registration,
                    complete_link_gate=complete_link_gate,
                    strata_gate=strata_gate,
                    source_preregistration=source_preregistration,
                )
            )
        except (MemoryError, RecursionError):
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "global_independence_gate_rebuild_invalid"
            ) from exc
        if gate_verification.get("status") != "PASS":
            raise ValueError("global_independence_gate_invalid")
        if global_gate.get("status") != "PASS":
            decision_blockers.append(
                "global_independence_gate_blocked:" + ":".join(identity)
            )
        entries.append(
            {
                "strategy_id": identity[0],
                "variant_id": identity[1],
                "lane": identity[2],
                "source_preregistration": source_preregistration,
                "strata_registration": strata_registration,
                "complete_link_gate": complete_link_gate,
                "strata_gate": strata_gate,
                "global_independence_gate": global_gate,
            }
        )

    document = seal_strict_canonical_document(
        {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "base_report_hash": base_hash,
            "base_strata_extension": deepcopy(base_strata_extension),
            "base_strata_extension_hash": base_strata_extension[
                "extension_hash"
            ],
            "entries": entries,
            "decision": "PASS" if not decision_blockers else "BLOCK",
            "decision_blockers": decision_blockers,
            "registry_binding_required": True,
            "global_independence_required": True,
            "consumer_only": True,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": dict(_PERMISSIONS),
        },
        "extension_hash",
    )
    self_verification = (
        verify_strategy_correlation_global_independence_report_extension(
            document,
            expected_base_report_hash=base_hash,
            expected_registry_bindings=normalized_bindings,
        )
    )
    if self_verification.get("status") != "PASS":
        raise ValueError(
            "global_independence_report_extension_self_verification_failed"
        )
    return document
