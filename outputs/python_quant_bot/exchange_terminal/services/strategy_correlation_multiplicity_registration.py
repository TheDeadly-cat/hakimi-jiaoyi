from __future__ import annotations

from copy import deepcopy
from typing import Any

from exchange_terminal.services.canonical_json_hash import canonical_hash
from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_multiplicity_audit import (
    build_strategy_correlation_multiplicity_policy,
    verify_strategy_correlation_multiplicity_audit,
)
from exchange_terminal.services.strategy_correlation_protocol_binding import (
    verify_strategy_correlation_protocol_registration,
)


STRATEGY_CORRELATION_MULTIPLICITY_FAMILY_REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-family-registration-v1"
)
STRATEGY_CORRELATION_MULTIPLICITY_FAMILY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-family-verification-v1"
)
STRATEGY_CORRELATION_MULTIPLICITY_BINDING_ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-binding-assessment-v1"
)
STRATEGY_CORRELATION_MULTIPLICITY_BINDING_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-binding-verification-v1"
)
SOURCE_REGISTRATION_SCHEMA_VERSION = "strategy-correlation-protocol-registration-v2"
FAMILY_FORMULA = (
    "C(total_symbols,2)-SUM(C(cluster_size,2))"
)


def _valid_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _family_definition(source_registration: dict[str, Any]) -> dict[str, Any] | None:
    if source_registration.get("schema_version") != SOURCE_REGISTRATION_SCHEMA_VERSION:
        return None
    if not _valid_hash(source_registration.get("registration_hash")):
        return None
    preregistration = source_registration.get("preregistration")
    if not isinstance(preregistration, dict):
        return None
    if not _valid_hash(preregistration.get("preregistration_hash")):
        return None
    symbols = preregistration.get("symbols")
    clusters = preregistration.get("clusters")
    if (
        not isinstance(symbols, list)
        or not symbols
        or not all(isinstance(symbol, str) and symbol for symbol in symbols)
        or len(set(symbols)) != len(symbols)
        or not isinstance(clusters, list)
        or len(clusters) < 2
    ):
        return None
    cluster_ids: set[str] = set()
    registered_members: list[str] = []
    cluster_sizes: list[int] = []
    for cluster in clusters:
        if not isinstance(cluster, dict) or set(cluster) != {"cluster_id", "members"}:
            return None
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if (
            not isinstance(cluster_id, str)
            or not cluster_id
            or cluster_id in cluster_ids
            or not isinstance(members, list)
            or not members
            or not all(isinstance(member, str) and member for member in members)
            or len(set(members)) != len(members)
        ):
            return None
        cluster_ids.add(cluster_id)
        registered_members.extend(members)
        cluster_sizes.append(len(members))
    if (
        len(set(registered_members)) != len(registered_members)
        or set(registered_members) != set(symbols)
    ):
        return None
    cluster_sizes.sort()
    symbol_count = len(symbols)
    total_pair_count = symbol_count * (symbol_count - 1) // 2
    within_cluster_pair_count = sum(
        size * (size - 1) // 2 for size in cluster_sizes
    )
    return {
        "formula": FAMILY_FORMULA,
        "symbol_count": symbol_count,
        "cluster_count": len(cluster_sizes),
        "cluster_sizes": cluster_sizes,
        "total_pair_count": total_pair_count,
        "within_cluster_pair_count": within_cluster_pair_count,
        "expected_cross_cluster_family_size": (
            total_pair_count - within_cluster_pair_count
        ),
    }


def _invalid_registration() -> dict[str, Any]:
    policy = build_strategy_correlation_multiplicity_policy()
    payload: dict[str, Any] = {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_FAMILY_REGISTRATION_SCHEMA_VERSION
        ),
        "status": "BLOCK",
        "source_protocol_registration": None,
        "source_registration_hash": "",
        "cluster_preregistration_hash": "",
        "multiplicity_policy": policy,
        "multiplicity_policy_hash": policy["policy_hash"],
        "family_definition": None,
        "input_scope": "PREREGISTRATION_ONLY",
        "source_before_returns_asserted": True,
        "requires_multiplicity_audit": True,
        "requires_protocol_upgrade": True,
        "requires_new_report_schema": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["family_registration_hash"] = canonical_hash(payload)
    return payload


def build_strategy_correlation_multiplicity_family_registration(
    source_protocol_registration: Any,
) -> dict[str, Any]:
    verification = verify_strategy_correlation_protocol_registration(
        source_protocol_registration
    )
    if (
        verification.get("status") != "PASS"
        or not isinstance(source_protocol_registration, dict)
    ):
        return _invalid_registration()
    family_definition = _family_definition(source_protocol_registration)
    if family_definition is None:
        return _invalid_registration()
    preregistration = source_protocol_registration["preregistration"]
    policy = build_strategy_correlation_multiplicity_policy()
    payload: dict[str, Any] = {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_FAMILY_REGISTRATION_SCHEMA_VERSION
        ),
        "status": "PREREGISTERED",
        "source_protocol_registration": deepcopy(source_protocol_registration),
        "source_registration_hash": source_protocol_registration["registration_hash"],
        "cluster_preregistration_hash": preregistration["preregistration_hash"],
        "multiplicity_policy": policy,
        "multiplicity_policy_hash": policy["policy_hash"],
        "family_definition": family_definition,
        "input_scope": "PREREGISTRATION_ONLY",
        "source_before_returns_asserted": True,
        "requires_multiplicity_audit": True,
        "requires_protocol_upgrade": True,
        "requires_new_report_schema": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["family_registration_hash"] = canonical_hash(payload)
    return payload


def verify_strategy_correlation_multiplicity_family_registration(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(document, dict):
        blockers.append("strategy_correlation_multiplicity_family_type_invalid")
        document = {}
    expected = build_strategy_correlation_multiplicity_family_registration(
        document.get("source_protocol_registration")
    )
    if not strict_json_contract_equal(document, expected):
        blockers.append("strategy_correlation_multiplicity_family_replay_mismatch")
    if authority_violations(document):
        blockers.append("strategy_correlation_multiplicity_family_authority_violation")
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_FAMILY_VERIFICATION_SCHEMA_VERSION
        ),
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "family_registration_hash": (
            expected["family_registration_hash"] if not blockers else ""
        ),
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def assess_strategy_correlation_multiplicity_binding(
    family_registration: Any,
    multiplicity_audit: Any,
) -> dict[str, Any]:
    registration_verification = (
        verify_strategy_correlation_multiplicity_family_registration(
            family_registration
        )
    )
    audit_verification = verify_strategy_correlation_multiplicity_audit(
        multiplicity_audit
    )
    registration = _mapping(family_registration)
    audit = _mapping(multiplicity_audit)
    source_registration = _mapping(registration.get("source_protocol_registration"))
    registered_preregistration = source_registration.get("preregistration")
    source_uncertainty = _mapping(audit.get("source_uncertainty_audit"))
    matrix_replay = _mapping(source_uncertainty.get("matrix_replay"))
    observed_preregistration = matrix_replay.get("preregistration")
    family_definition = _mapping(registration.get("family_definition"))

    registration_valid = (
        registration_verification.get("status") == "PASS"
        and registration.get("status") == "PREREGISTERED"
    )
    audit_valid = audit_verification.get("status") == "PASS"
    source_registration_hash_bound = (
        registration_valid
        and registration.get("source_registration_hash")
        == source_registration.get("registration_hash")
    )
    preregistration_bound = (
        registration_valid
        and audit_valid
        and registered_preregistration == observed_preregistration
    )
    family_size_bound = (
        registration_valid
        and audit_valid
        and family_definition.get("expected_cross_cluster_family_size")
        == audit.get("family_size")
    )
    policy_bound = (
        registration_valid
        and audit_valid
        and registration.get("multiplicity_policy_hash") == audit.get("policy_hash")
        and registration.get("multiplicity_policy") == audit.get("policy")
    )
    local_chain_bound = all((
        registration_valid,
        audit_valid,
        source_registration_hash_bound,
        preregistration_bound,
        family_size_bound,
        policy_bound,
    ))
    local_decision_status = (
        "PASS" if local_chain_bound and audit.get("status") == "PASS" else "BLOCK"
    )

    blockers: list[str] = []
    blockers.extend(
        f"registration:{item}"
        for item in registration_verification.get("blockers") or []
    )
    blockers.extend(
        f"audit:{item}" for item in audit_verification.get("blockers") or []
    )
    if registration_valid and not source_registration_hash_bound:
        blockers.append("multiplicity_source_registration_hash_mismatch")
    if registration_valid and audit_valid and not preregistration_bound:
        blockers.append("multiplicity_preregistration_mismatch")
    if registration_valid and audit_valid and not family_size_bound:
        blockers.append("multiplicity_family_size_mismatch")
    if registration_valid and audit_valid and not policy_bound:
        blockers.append("multiplicity_policy_mismatch")
    if local_chain_bound and audit.get("status") != "PASS":
        blockers.append("multiplicity_audit_decision_block")
    if local_chain_bound and audit.get("status") == "PASS":
        blockers.append("multiplicity_new_protocol_and_report_consumer_required")
    blockers = list(dict.fromkeys(blockers))

    if not registration_valid:
        next_evidence = "VALID_MULTIPLICITY_FAMILY_REGISTRATION"
    elif not audit_valid:
        next_evidence = "VALID_MULTIPLICITY_AUDIT"
    elif not preregistration_bound:
        next_evidence = "MATCH_PREREGISTERED_CLUSTER_PARTITION"
    elif not family_size_bound:
        next_evidence = "MATCH_PREREGISTERED_FAMILY_SIZE"
    elif not policy_bound:
        next_evidence = "MATCH_PREREGISTERED_MULTIPLICITY_POLICY"
    elif audit.get("status") != "PASS":
        next_evidence = "RESOLVE_MULTIPLICITY_BLOCK_OR_REREGISTER"
    else:
        next_evidence = "NEW_PROTOCOL_AND_REPORT_CONSUMER"

    payload: dict[str, Any] = {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_BINDING_ASSESSMENT_SCHEMA_VERSION
        ),
        "status": "BLOCK",
        "local_chain_status": "PASS" if local_chain_bound else "BLOCK",
        "local_decision_status": local_decision_status,
        "family_registration_status": (
            "PASS" if registration_valid else "BLOCK"
        ),
        "multiplicity_audit_status": "PASS" if audit_valid else "BLOCK",
        "source_registration_hash_bound": source_registration_hash_bound,
        "preregistration_bound": preregistration_bound,
        "family_size_bound": family_size_bound,
        "policy_bound": policy_bound,
        "expected_family_size": (
            family_definition.get("expected_cross_cluster_family_size")
            if registration_valid else None
        ),
        "observed_family_size": audit.get("family_size") if audit_valid else None,
        "formal_protocol_bound": False,
        "current_report_schema_bound": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "parameter_selection_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "next_evidence_required": next_evidence,
        "blockers": blockers,
    }
    payload["assessment_hash"] = canonical_hash(payload)
    return payload


def verify_strategy_correlation_multiplicity_binding_assessment(
    document: Any,
    *,
    family_registration: Any,
    multiplicity_audit: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(document, dict):
        blockers.append("strategy_correlation_multiplicity_binding_type_invalid")
    expected = assess_strategy_correlation_multiplicity_binding(
        family_registration,
        multiplicity_audit,
    )
    if not strict_json_contract_equal(document, expected):
        blockers.append("strategy_correlation_multiplicity_binding_replay_mismatch")
    if authority_violations(document):
        blockers.append("strategy_correlation_multiplicity_binding_authority_violation")
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_BINDING_VERIFICATION_SCHEMA_VERSION
        ),
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "assessment_hash": expected["assessment_hash"] if not blockers else "",
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
