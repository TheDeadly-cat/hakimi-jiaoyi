"""Candidate-only report21 binding for the temporal date-grid consumer."""

from __future__ import annotations

from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
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
from exchange_terminal.services.strategy_correlation_cluster_temporal_stability_report_binding import (
    ASSESSMENT_SCHEMA_VERSION as SOURCE_ASSESSMENT_SCHEMA_VERSION,
    assess_strategy_correlation_cluster_temporal_stability_report_binding,
    verify_strategy_correlation_cluster_temporal_stability_report_binding,
)


ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-report21-binding-assessment-v1"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-temporal-date-grid-report21-binding-assessment-v1-verification-v1"
)

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
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


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _identity(value: Any) -> tuple[str, str, str] | None:
    if type(value) is not dict:
        return None
    identity = tuple(
        value.get(field) for field in ("strategy_id", "variant_id", "lane")
    )
    if not all(
        type(part) is str and part and part == part.strip()
        for part in identity
    ):
        return None
    return identity  # type: ignore[return-value]


def _binding_id(value: Any) -> str:
    if type(value) is not str or not value or value != value.strip():
        return ""
    return value


def _binding_index(
    values: Any,
    *,
    expected_fields: set[str],
    hash_field: str,
) -> dict[tuple[str, str, str], dict[str, Any]] | None:
    if type(values) is not list:
        return None
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        identity = _identity(value)
        if (
            identity is None
            or type(value) is not dict
            or set(value) != expected_fields
            or not _is_sha256(value.get(hash_field))
            or identity in result
        ):
            return None
        if expected_fields == _TEMPORAL_BINDING_FIELDS and (
            type(value.get("source_uncertainty_audit")) is not dict
            or type(value.get("correlation_matrix")) is not dict
            or type(value.get("selection_cells")) is not list
        ):
            return None
        result[identity] = value
    return result


def _entry_index(
    values: Any,
    *,
    required_mapping_fields: tuple[str, ...],
) -> dict[tuple[str, str, str], dict[str, Any]] | None:
    if type(values) is not list or not values:
        return None
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        identity = _identity(value)
        if (
            identity is None
            or identity in result
            or any(type(value.get(field)) is not dict for field in required_mapping_fields)
        ):
            return None
        result[identity] = value
    return result


def _report_indexes(
    report21_extension: Any,
) -> tuple[
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
        or set(report_entries) != set(stability_entries)
        or set(report_entries) != set(source_entries)
    ):
        return None
    return report_entries, stability_entries, source_entries


def _verification(
    blockers: list[str],
    *,
    candidate_bound: bool = False,
    report21_decision: str = "UNKNOWN",
    date_grid_decision: str = "UNKNOWN",
) -> dict[str, Any]:
    unique = list(dict.fromkeys(blockers))
    status = "PASS" if not unique else "BLOCK"
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "blockers": unique,
        "candidate_bound": candidate_bound if status == "PASS" else False,
        "report21_decision": report21_decision if status == "PASS" else "UNKNOWN",
        "date_grid_decision": date_grid_decision if status == "PASS" else "UNKNOWN",
        "candidate_only": True,
        "protocol_date_grid_policy_preregistered": False,
        "report21_schema_contains_date_grid_gate": False,
        "formal_registration_report_binding": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def assess_strategy_correlation_cluster_temporal_date_grid_report_binding(
    protocol_registration: Any,
    report21_extension: Any,
    *,
    binding_id: Any,
    expected_protocol_registration_hash: Any,
    expected_report21_extension_hash: Any,
    expected_report_identity_set_hash: Any,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    expected_temporal_stability_bindings: Any,
    expected_temporal_date_grid_bindings: Any,
) -> dict[str, Any]:
    normalized_binding_id = _binding_id(binding_id)
    source_arguments = {
        "protocol_registration": protocol_registration,
        "report21_extension": report21_extension,
        "binding_id": binding_id,
        "expected_protocol_registration_hash": expected_protocol_registration_hash,
        "expected_report21_extension_hash": expected_report21_extension_hash,
        "expected_report_identity_set_hash": expected_report_identity_set_hash,
        "expected_base_report_hash": expected_base_report_hash,
        "expected_global_independence_extension_hash": (
            expected_global_independence_extension_hash
        ),
        "expected_cluster_stability_extension_hash": (
            expected_cluster_stability_extension_hash
        ),
        "expected_registry_bindings": expected_registry_bindings,
        "expected_stability_bindings": expected_stability_bindings,
        "expected_temporal_stability_bindings": (
            expected_temporal_stability_bindings
        ),
    }
    try:
        source_assessment = (
            assess_strategy_correlation_cluster_temporal_stability_report_binding(
                protocol_registration,
                report21_extension,
                **{
                    key: value
                    for key, value in source_arguments.items()
                    if key not in {"protocol_registration", "report21_extension"}
                },
            )
        )
        source_verification = (
            verify_strategy_correlation_cluster_temporal_stability_report_binding(
                source_assessment,
                **source_arguments,
            )
        )
    except (KeyError, TypeError, ValueError):
        source_assessment = {}
        source_verification = {"status": "BLOCK", "candidate_bound": False}

    report_indexes = _report_indexes(report21_extension)
    temporal_bindings = _binding_index(
        expected_temporal_stability_bindings,
        expected_fields=_TEMPORAL_BINDING_FIELDS,
        hash_field="expected_temporal_stability_gate_hash",
    )
    date_grid_bindings = _binding_index(
        expected_temporal_date_grid_bindings,
        expected_fields=_DATE_GRID_BINDING_FIELDS,
        hash_field="expected_temporal_date_grid_gate_hash",
    )
    report_identity_set = (
        set(report_indexes[0]) if report_indexes is not None else set()
    )
    binding_set_exact = (
        report_indexes is not None
        and temporal_bindings is not None
        and date_grid_bindings is not None
        and set(temporal_bindings) == report_identity_set
        and set(date_grid_bindings) == report_identity_set
    )

    gate_contracts_verified = binding_set_exact
    gate_hashes_bound = binding_set_exact
    consumer_locks_preserved = binding_set_exact
    gate_results: list[dict[str, Any]] = []
    if (
        binding_set_exact
        and report_indexes is not None
        and temporal_bindings is not None
        and date_grid_bindings is not None
    ):
        report_entries, stability_entries, source_entries = report_indexes
        for identity in sorted(report_identity_set):
            report_entry = report_entries[identity]
            stability_entry = stability_entries[identity]
            source_entry = source_entries[identity]
            temporal_binding = temporal_bindings[identity]
            date_grid_binding = date_grid_bindings[identity]
            try:
                gate = evaluate_strategy_correlation_cluster_temporal_date_grid_gate(
                    temporal_binding["source_uncertainty_audit"],
                    report_entry["temporal_stability_gate"],
                    full_window_stability_gate=stability_entry["stability_gate"],
                    complete_link_gate=source_entry["complete_link_gate"],
                    preregistration=source_entry["source_preregistration"],
                    correlation_matrix=temporal_binding["correlation_matrix"],
                    selection_cells=temporal_binding["selection_cells"],
                    strategy_id=identity[0],
                    variant_id=identity[1],
                    lane=identity[2],
                )
                verification = (
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
                        complete_link_gate=source_entry["complete_link_gate"],
                        preregistration=source_entry["source_preregistration"],
                        correlation_matrix=temporal_binding[
                            "correlation_matrix"
                        ],
                        selection_cells=temporal_binding["selection_cells"],
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
                gate = {}
                verification = {"status": "BLOCK", "decision_status": "BLOCK"}
            contract_verified = verification.get("status") == "PASS"
            hash_bound = (
                _is_sha256(gate.get("gate_hash"))
                and gate.get("gate_hash")
                == date_grid_binding["expected_temporal_date_grid_gate_hash"]
            )
            consumer_locked = (
                gate.get("consumer_only") is True
                and gate.get("writer_available") is False
                and gate.get("current_admission_allowed") is False
                and gate.get("current_writer_activation_allowed") is False
                and gate.get("permissions") == _PERMISSIONS
            )
            gate_contracts_verified = gate_contracts_verified and contract_verified
            gate_hashes_bound = gate_hashes_bound and hash_bound
            consumer_locks_preserved = consumer_locks_preserved and consumer_locked
            gate_results.append(
                {
                    "strategy_id": identity[0],
                    "variant_id": identity[1],
                    "lane": identity[2],
                    "source_temporal_gate_hash": report_entry[
                        "temporal_stability_gate"
                    ].get("gate_hash", ""),
                    "temporal_date_grid_gate_hash": gate.get("gate_hash", ""),
                    "gate_hash_bound": hash_bound,
                    "contract_status": verification.get("status", "BLOCK"),
                    "decision_status": verification.get(
                        "decision_status", "BLOCK"
                    ),
                }
            )

    date_grid_decision = (
        "PASS"
        if binding_set_exact
        and gate_contracts_verified
        and gate_results
        and all(item["decision_status"] == "PASS" for item in gate_results)
        else "BLOCK"
        if binding_set_exact and gate_contracts_verified and gate_results
        else "UNKNOWN"
    )
    report21_decision = (
        source_assessment.get("report21_decision", "UNKNOWN")
        if source_verification.get("status") == "PASS"
        else "UNKNOWN"
    )
    report_pass_consistent = (
        report21_decision != "PASS" or date_grid_decision == "PASS"
    )
    facts = {
        "source_report_binding_independently_verified": (
            source_verification.get("status") == "PASS"
        ),
        "source_report_candidate_bound": (
            source_verification.get("candidate_bound") is True
        ),
        "date_grid_binding_set_exact": binding_set_exact,
        "date_grid_gate_contracts_verified": gate_contracts_verified,
        "date_grid_gate_hashes_bound": gate_hashes_bound,
        "date_grid_consumer_locks_preserved": consumer_locks_preserved,
        "report21_pass_requires_all_date_grid_pass": report_pass_consistent,
    }
    blockers = [name for name, passed in facts.items() if passed is not True]
    if not normalized_binding_id:
        blockers.insert(0, "binding_id_invalid")
    candidate_bound = not blockers
    normalized_gate_results = sorted(
        gate_results,
        key=lambda item: (
            item["strategy_id"],
            item["variant_id"],
            item["lane"],
        ),
    )
    assessment = {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "binding_id": normalized_binding_id,
        "source_assessment_schema_version": SOURCE_ASSESSMENT_SCHEMA_VERSION,
        "source_report_binding_assessment_hash": source_assessment.get(
            "assessment_hash", ""
        ),
        "report21_extension_hash": (
            report21_extension.get("extension_hash", "")
            if type(report21_extension) is dict
            else ""
        ),
        "temporal_date_grid_gate_schema_version": (
            TEMPORAL_DATE_GRID_GATE_SCHEMA_VERSION
        ),
        "report_identity_count": len(report_identity_set),
        "temporal_date_grid_gate_count": len(normalized_gate_results),
        "temporal_date_grid_gate_pass_count": sum(
            item["decision_status"] == "PASS"
            for item in normalized_gate_results
        ),
        "temporal_date_grid_binding_set_hash": strict_canonical_hash(
            normalized_gate_results
        ),
        "facts": facts,
        "blockers": blockers,
        "status": "CANDIDATE_BOUND" if candidate_bound else "BLOCK",
        "report21_decision": report21_decision,
        "date_grid_decision": date_grid_decision,
        "report21_decision_authority": False,
        "date_grid_decision_authority": False,
        "candidate_bound": candidate_bound,
        "candidate_only": True,
        "external_assets_embedded": False,
        "requires_caller_independent_hashes": True,
        "protocol_date_grid_policy_preregistered": False,
        "report21_schema_contains_date_grid_gate": False,
        "requires_report_schema_upgrade": True,
        "formal_registration_report_binding": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(assessment, "assessment_hash")


def verify_strategy_correlation_cluster_temporal_date_grid_report_binding(
    document: Any,
    *,
    protocol_registration: Any,
    report21_extension: Any,
    binding_id: Any,
    expected_protocol_registration_hash: Any,
    expected_report21_extension_hash: Any,
    expected_report_identity_set_hash: Any,
    expected_base_report_hash: Any,
    expected_global_independence_extension_hash: Any,
    expected_cluster_stability_extension_hash: Any,
    expected_registry_bindings: Any,
    expected_stability_bindings: Any,
    expected_temporal_stability_bindings: Any,
    expected_temporal_date_grid_bindings: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        blockers.append("temporal_date_grid_report_binding_invalid")
    elif strict_research_authority_violations(document):
        blockers.append("research_authority_violation")
    try:
        expected = (
            assess_strategy_correlation_cluster_temporal_date_grid_report_binding(
                protocol_registration,
                report21_extension,
                binding_id=binding_id,
                expected_protocol_registration_hash=(
                    expected_protocol_registration_hash
                ),
                expected_report21_extension_hash=expected_report21_extension_hash,
                expected_report_identity_set_hash=expected_report_identity_set_hash,
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
                expected_temporal_date_grid_bindings=(
                    expected_temporal_date_grid_bindings
                ),
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
        return _verification(["temporal_date_grid_report_binding_source_invalid"])
    if type(document) is not dict or not strict_json_contract_equal(document, expected):
        blockers.append("temporal_date_grid_report_binding_contract_invalid")
    return _verification(
        blockers,
        candidate_bound=expected["candidate_bound"],
        report21_decision=expected["report21_decision"],
        date_grid_decision=expected["date_grid_decision"],
    )


__all__ = [
    "ASSESSMENT_SCHEMA_VERSION",
    "SOURCE_ASSESSMENT_SCHEMA_VERSION",
    "TEMPORAL_DATE_GRID_GATE_SCHEMA_VERSION",
    "VERIFICATION_SCHEMA_VERSION",
    "assess_strategy_correlation_cluster_temporal_date_grid_report_binding",
    "verify_strategy_correlation_cluster_temporal_date_grid_report_binding",
]
