"""Deterministic in-memory builder for verified report18 strata evidence."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from exchange_terminal.services.strategy_correlation_complete_link_report_consumer import (
    verify_strategy_correlation_complete_link_report_extension,
)
from exchange_terminal.services.strategy_correlation_preregistered_strata import (
    build_strategy_correlation_strata_preregistration,
    evaluate_strategy_correlation_strata_gate,
    verify_strategy_correlation_strata_gate,
    verify_strategy_correlation_strata_preregistration,
)
from exchange_terminal.services.strategy_correlation_strata_registry import (
    assess_strategy_correlation_strata_registry_binding,
    verify_strategy_correlation_strata_registry_asset,
    verify_strategy_correlation_strata_registry_binding,
)
from exchange_terminal.services.strategy_correlation_strata_report_consumer import (
    BASE_PROTOCOL_SCHEMA_VERSION,
    BASE_REPORT_SCHEMA_VERSION,
    EXTENSION_SCHEMA_VERSION,
    TARGET_PROTOCOL_SCHEMA_VERSION,
    TARGET_REPORT_SCHEMA_VERSION,
    verify_strategy_correlation_strata_report_extension,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
)


INPUT_SCHEMA_VERSION = "strategy-correlation-strata-extension-builder-input-v1"
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_LANES = frozenset({"RAW_EXCESS", "RISK_ADJUSTED"})
_INPUT_FIELDS = frozenset(
    {
        "schema_version",
        "strategy_id",
        "variant_id",
        "lane",
        "dimensions",
        "registry_asset",
        "selection_cutoff_date",
        "expected_registry_asset_hash",
        "expected_classification_source_hash",
    }
)
_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _identity(value: Any) -> tuple[str, str, str]:
    if type(value) is not dict:
        raise ValueError("strata_builder_identity_contract_invalid")
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
        or lane not in _LANES
    ):
        raise ValueError("strata_builder_identity_invalid")
    return strategy_id, variant_id, lane


def _clean_hash(value: Any, *, field: str) -> str:
    if type(value) is not str or _HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field}_invalid")
    return value


def _normalize_inputs(
    values: Any,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    if type(values) is not list or not values:
        raise ValueError("strata_builder_inputs_invalid")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        if type(value) is not dict or set(value) != _INPUT_FIELDS:
            raise ValueError("strata_builder_input_contract_invalid")
        if value.get("schema_version") != INPUT_SCHEMA_VERSION:
            raise ValueError("strata_builder_input_schema_invalid")
        identity = _identity(value)
        if identity in result:
            raise ValueError("strata_builder_input_identity_duplicate")
        if type(value.get("dimensions")) is not list or not value["dimensions"]:
            raise ValueError("strata_builder_dimensions_invalid")
        if type(value.get("registry_asset")) is not dict:
            raise ValueError("strata_builder_registry_asset_invalid")
        cutoff = value.get("selection_cutoff_date")
        if (
            type(cutoff) is not str
            or not cutoff
            or cutoff != cutoff.strip()
        ):
            raise ValueError("strata_builder_selection_cutoff_invalid")
        _clean_hash(
            value.get("expected_registry_asset_hash"),
            field="expected_registry_asset_hash",
        )
        _clean_hash(
            value.get("expected_classification_source_hash"),
            field="expected_classification_source_hash",
        )
        result[identity] = value
    return result


def _expected_binding(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy_id": value["strategy_id"],
        "variant_id": value["variant_id"],
        "lane": value["lane"],
        "selection_cutoff_date": value["selection_cutoff_date"],
        "expected_registry_asset_hash": value[
            "expected_registry_asset_hash"
        ],
        "expected_classification_source_hash": value[
            "expected_classification_source_hash"
        ],
    }


def build_strategy_correlation_strata_report_extension(
    base_complete_link_extension: Any,
    *,
    expected_base_report_hash: Any,
    strata_inputs: Any,
) -> dict[str, Any]:
    """Build report18 without persistence, activation, or external assertions."""

    if type(base_complete_link_extension) is not dict:
        raise ValueError("base_complete_link_extension_invalid")
    base_verification = verify_strategy_correlation_complete_link_report_extension(
        base_complete_link_extension,
        expected_base_report_hash=expected_base_report_hash,
    )
    if base_verification.get("status") != "PASS":
        raise ValueError("base_complete_link_extension_invalid")
    normalized_base_hash = _clean_hash(
        expected_base_report_hash,
        field="expected_base_report_hash",
    )
    input_map = _normalize_inputs(strata_inputs)

    base_entry_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for base_entry in base_complete_link_extension.get("entries", []):
        identity = _identity(base_entry)
        if identity in base_entry_map:
            raise ValueError("base_complete_link_entry_duplicate")
        base_entry_map[identity] = base_entry
    if not base_entry_map or set(base_entry_map) != set(input_map):
        raise ValueError("strata_builder_input_identity_binding_invalid")

    entries: list[dict[str, Any]] = []
    expected_bindings: list[dict[str, Any]] = []
    decision_blockers: list[str] = []
    if base_complete_link_extension.get("decision") != "PASS":
        decision_blockers.append("complete_link_extension_blocked")

    for identity in sorted(base_entry_map):
        base_entry = base_entry_map[identity]
        source_input = input_map[identity]
        source_preregistration = deepcopy(base_entry["preregistration"])
        complete_link_gate = deepcopy(base_entry["gate_v2"])
        dimensions = deepcopy(source_input["dimensions"])
        registry_asset = deepcopy(source_input["registry_asset"])

        asset_verification = verify_strategy_correlation_strata_registry_asset(
            registry_asset,
            source_preregistration=source_preregistration,
        )
        if asset_verification.get("status") != "PASS":
            raise ValueError("strata_builder_registry_asset_invalid")

        try:
            registration = build_strategy_correlation_strata_preregistration(
                source_preregistration,
                dimensions,
            )
            registration_verification = (
                verify_strategy_correlation_strata_preregistration(
                    registration,
                    source_preregistration=source_preregistration,
                )
            )
            strata_gate = evaluate_strategy_correlation_strata_gate(
                registration,
                complete_link_gate,
                source_preregistration=source_preregistration,
            )
            gate_verification = verify_strategy_correlation_strata_gate(
                strata_gate,
                registration=registration,
                complete_link_gate=complete_link_gate,
                source_preregistration=source_preregistration,
            )
            registry_binding = assess_strategy_correlation_strata_registry_binding(
                registry_asset,
                registration,
                source_preregistration,
                selection_cutoff_date=source_input["selection_cutoff_date"],
                expected_registry_asset_hash=source_input[
                    "expected_registry_asset_hash"
                ],
                expected_classification_source_hash=source_input[
                    "expected_classification_source_hash"
                ],
            )
            binding_verification = (
                verify_strategy_correlation_strata_registry_binding(
                    registry_binding,
                    registry_asset=registry_asset,
                    registration=registration,
                    source_preregistration=source_preregistration,
                    selection_cutoff_date=source_input[
                        "selection_cutoff_date"
                    ],
                    expected_registry_asset_hash=source_input[
                        "expected_registry_asset_hash"
                    ],
                    expected_classification_source_hash=source_input[
                        "expected_classification_source_hash"
                    ],
                )
            )
        except (MemoryError, RecursionError):
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("strata_builder_rebuild_invalid") from exc

        if registration_verification.get("status") != "PASS":
            raise ValueError("strata_builder_registration_invalid")
        if gate_verification.get("status") != "PASS":
            raise ValueError("strata_builder_gate_invalid")
        if binding_verification.get("status") != "PASS":
            raise ValueError("strata_builder_registry_binding_invalid")

        identity_label = ":".join(identity)
        if strata_gate.get("status") != "PASS":
            decision_blockers.append(
                f"strata_gate_blocked:{identity_label}"
            )
        if registry_binding.get("status") != "BOUND":
            decision_blockers.append(
                f"strata_registry_binding_blocked:{identity_label}"
            )
        entries.append(
            {
                "strategy_id": identity[0],
                "variant_id": identity[1],
                "lane": identity[2],
                "source_preregistration": source_preregistration,
                "strata_registration": registration,
                "complete_link_gate": complete_link_gate,
                "strata_gate": strata_gate,
                "registry_asset": registry_asset,
                "registry_binding": registry_binding,
            }
        )
        expected_bindings.append(_expected_binding(source_input))

    document = seal_strict_canonical_document(
        {
            "schema_version": EXTENSION_SCHEMA_VERSION,
            "base_report_schema_version": BASE_REPORT_SCHEMA_VERSION,
            "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
            "base_protocol_schema_version": BASE_PROTOCOL_SCHEMA_VERSION,
            "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
            "base_report_hash": normalized_base_hash,
            "base_complete_link_extension": deepcopy(
                base_complete_link_extension
            ),
            "base_complete_link_extension_hash": (
                base_complete_link_extension["extension_hash"]
            ),
            "entries": entries,
            "decision": "PASS" if not decision_blockers else "BLOCK",
            "decision_blockers": decision_blockers,
            "registry_binding_required": True,
            "consumer_only": True,
            "writer_available": False,
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "permissions": dict(_PERMISSIONS),
        },
        "extension_hash",
    )
    self_verification = verify_strategy_correlation_strata_report_extension(
        document,
        expected_base_report_hash=normalized_base_hash,
        expected_registry_bindings=expected_bindings,
    )
    if self_verification.get("status") != "PASS":
        raise ValueError("strata_report_extension_self_verification_failed")
    return document
