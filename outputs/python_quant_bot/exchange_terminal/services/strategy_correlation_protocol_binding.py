from __future__ import annotations

from copy import deepcopy
from datetime import date
import re
from typing import Any

from .strategy_correlation_cluster_gate import (
    authority_violations,
    verify_correlation_cluster_preregistration,
)
from .strategy_correlation_return_replay import verify_replayed_correlation_cluster_gate
from .strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_policy,
    verify_strategy_correlation_uncertainty_audit,
    verify_strategy_correlation_uncertainty_policy,
)
from .strategy_matrix_protocol import (
    STRATEGY_CORRELATION_CLUSTER_REPORT_SCHEMA_VERSION,
    STRATEGY_MATRIX_PROTOCOL_CORRELATION_VERSION,
    canonical_hash,
    verify_strategy_matrix_protocol,
)
from .strategy_research_protocol_artifact import (
    verify_bound_strategy_research_protocol_artifact,
)
from .strict_canonical_json_hash import strict_json_contract_equal


STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-v1"
)
STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2 = (
    "strategy-correlation-protocol-registration-v2"
)
STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-registration-verification-v2"
)
STRATEGY_CORRELATION_PROTOCOL_BINDING_ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-protocol-binding-assessment-v3"
)
STRATEGY_CORRELATION_PROTOCOL_BINDING_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-protocol-binding-verification-v3"
)
TARGET_PROTOCOL_SCHEMA_VERSION = STRATEGY_MATRIX_PROTOCOL_CORRELATION_VERSION
TARGET_REPORT_SCHEMA_VERSION = STRATEGY_CORRELATION_CLUSTER_REPORT_SCHEMA_VERSION
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_LANES = frozenset({"RAW_EXCESS", "RISK_ADJUSTED"})
_EVALUATION_FIELDS = frozenset({"strategy_id", "variant_id", "lane"})
_REGISTRATION_FIELDS_V1 = frozenset({
    "schema_version",
    "target_protocol_schema_version",
    "target_report_schema_version",
    "cutoff_date",
    "selection_alignment_input_hash",
    "preregistration",
    "evaluations",
    "evaluation_count",
    "current_writer_activation_allowed",
    "current_admission_allowed",
    "requires_protocol_upgrade",
    "requires_new_report_schema",
    "permissions",
    "registration_hash",
})
_REGISTRATION_FIELDS_V2 = _REGISTRATION_FIELDS_V1 | frozenset({
    "uncertainty_policy",
    "uncertainty_policy_hash",
    "requires_uncertainty_audit",
})


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _valid_cutoff_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _canonical_evaluations(value: Any) -> tuple[list[dict[str, str]], list[str]]:
    blockers: list[str] = []
    if not isinstance(value, list) or not value or len(value) > 256:
        return [], ["strategy_correlation_registration_evaluations_invalid"]
    normalized: list[dict[str, str]] = []
    identities: set[tuple[str, str, str]] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != _EVALUATION_FIELDS:
            blockers.append(f"strategy_correlation_registration_evaluation_fields:{index}")
            continue
        strategy_id = item.get("strategy_id")
        variant_id = item.get("variant_id")
        lane = item.get("lane")
        if not isinstance(strategy_id, str) or not _IDENTITY_RE.fullmatch(strategy_id):
            blockers.append(f"strategy_correlation_registration_strategy_id:{index}")
            continue
        if not isinstance(variant_id, str) or not _IDENTITY_RE.fullmatch(variant_id):
            blockers.append(f"strategy_correlation_registration_variant_id:{index}")
            continue
        if lane not in _LANES:
            blockers.append(f"strategy_correlation_registration_lane:{index}")
            continue
        identity = (strategy_id, variant_id, lane)
        if identity in identities:
            blockers.append(f"strategy_correlation_registration_evaluation_duplicate:{index}")
            continue
        identities.add(identity)
        normalized.append({
            "strategy_id": strategy_id,
            "variant_id": variant_id,
            "lane": lane,
        })
    normalized.sort(key=lambda item: (item["strategy_id"], item["variant_id"], item["lane"]))
    return normalized, blockers


def _registration_blockers(document: Any) -> list[str]:
    if not isinstance(document, dict):
        return ["strategy_correlation_registration_type_invalid"]
    blockers: list[str] = []
    registration_schema = document.get("schema_version")
    expected_fields = (
        _REGISTRATION_FIELDS_V2
        if registration_schema == STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2
        else _REGISTRATION_FIELDS_V1
    )
    if set(document) != expected_fields:
        blockers.append("strategy_correlation_registration_fields_invalid")
    if registration_schema not in {
        STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION,
        STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2,
    }:
        blockers.append("strategy_correlation_registration_schema_invalid")
    if document.get("target_protocol_schema_version") != TARGET_PROTOCOL_SCHEMA_VERSION:
        blockers.append("strategy_correlation_registration_protocol_target_invalid")
    if document.get("target_report_schema_version") != TARGET_REPORT_SCHEMA_VERSION:
        blockers.append("strategy_correlation_registration_report_target_invalid")
    if not _valid_cutoff_date(document.get("cutoff_date")):
        blockers.append("strategy_correlation_registration_cutoff_invalid")
    if not _valid_sha256(document.get("selection_alignment_input_hash")):
        blockers.append("strategy_correlation_registration_alignment_hash_invalid")

    preregistration = document.get("preregistration")
    preregistration_verification = verify_correlation_cluster_preregistration(preregistration)
    if preregistration_verification.get("status") != "PASS":
        blockers.extend(
            f"strategy_correlation_registration_preregistration:{item}"
            for item in preregistration_verification.get("blockers") or ["verification_blocked"]
        )

    canonical_evaluations, evaluation_blockers = _canonical_evaluations(
        document.get("evaluations")
    )
    blockers.extend(evaluation_blockers)
    if document.get("evaluations") != canonical_evaluations:
        blockers.append("strategy_correlation_registration_evaluations_noncanonical")
    if (
        isinstance(document.get("evaluation_count"), bool)
        or document.get("evaluation_count") != len(canonical_evaluations)
    ):
        blockers.append("strategy_correlation_registration_evaluation_count_invalid")

    if registration_schema == STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2:
        uncertainty_policy_verification = verify_strategy_correlation_uncertainty_policy(
            document.get("uncertainty_policy")
        )
        blockers.extend(
            f"strategy_correlation_registration_uncertainty_policy:{item}"
            for item in uncertainty_policy_verification.get("blockers") or []
        )
        if document.get("uncertainty_policy_hash") != uncertainty_policy_verification.get(
            "policy_hash"
        ):
            blockers.append("strategy_correlation_registration_uncertainty_policy_hash_mismatch")
        if document.get("requires_uncertainty_audit") is not True:
            blockers.append("strategy_correlation_registration_uncertainty_boundary_invalid")

    permissions = document.get("permissions")
    if permissions != {"paper_authorized": False, "live_order_allowed": False}:
        blockers.append("strategy_correlation_registration_permissions_invalid")
    if document.get("current_writer_activation_allowed") is not False:
        blockers.append("strategy_correlation_registration_writer_authority_invalid")
    if document.get("current_admission_allowed") is not False:
        blockers.append("strategy_correlation_registration_admission_authority_invalid")
    if document.get("requires_protocol_upgrade") is not True:
        blockers.append("strategy_correlation_registration_upgrade_boundary_invalid")
    if document.get("requires_new_report_schema") is not True:
        blockers.append("strategy_correlation_registration_report_boundary_invalid")
    if authority_violations(document):
        blockers.append("strategy_correlation_registration_authority_violation")

    clean = dict(document)
    registration_hash = clean.pop("registration_hash", None)
    if not _valid_sha256(registration_hash) or canonical_hash(clean) != registration_hash:
        blockers.append("strategy_correlation_registration_hash_invalid")
    return list(dict.fromkeys(blockers))


def build_strategy_correlation_protocol_registration(
    preregistration: dict[str, Any],
    *,
    cutoff_date: str,
    selection_alignment_input_hash: str,
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    canonical_evaluations, evaluation_blockers = _canonical_evaluations(evaluations)
    if evaluation_blockers:
        raise ValueError("invalid strategy-correlation evaluations")
    payload: dict[str, Any] = {
        "schema_version": STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "cutoff_date": cutoff_date,
        "selection_alignment_input_hash": selection_alignment_input_hash,
        "preregistration": deepcopy(preregistration),
        "evaluations": canonical_evaluations,
        "evaluation_count": len(canonical_evaluations),
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_protocol_upgrade": True,
        "requires_new_report_schema": True,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["registration_hash"] = canonical_hash(payload)
    verification = verify_strategy_correlation_protocol_registration(payload)
    if verification["status"] != "PASS":
        raise ValueError("invalid strategy-correlation protocol registration")
    return payload


def build_strategy_correlation_protocol_registration_v2(
    preregistration: dict[str, Any],
    *,
    cutoff_date: str,
    selection_alignment_input_hash: str,
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    canonical_evaluations, evaluation_blockers = _canonical_evaluations(evaluations)
    if evaluation_blockers:
        raise ValueError("invalid strategy-correlation evaluations")
    uncertainty_policy = build_strategy_correlation_uncertainty_policy()
    payload: dict[str, Any] = {
        "schema_version": STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2,
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "cutoff_date": cutoff_date,
        "selection_alignment_input_hash": selection_alignment_input_hash,
        "preregistration": deepcopy(preregistration),
        "evaluations": canonical_evaluations,
        "evaluation_count": len(canonical_evaluations),
        "uncertainty_policy": uncertainty_policy,
        "uncertainty_policy_hash": uncertainty_policy["policy_hash"],
        "requires_uncertainty_audit": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_protocol_upgrade": True,
        "requires_new_report_schema": True,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["registration_hash"] = canonical_hash(payload)
    verification = verify_strategy_correlation_protocol_registration(payload)
    if verification["status"] != "PASS":
        raise ValueError("invalid strategy-correlation protocol registration v2")
    return payload


def verify_strategy_correlation_protocol_registration(document: Any) -> dict[str, Any]:
    blockers = _registration_blockers(document)
    return {
        "schema_version": STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "registration_hash": (
            str(document.get("registration_hash") or "")
            if isinstance(document, dict) and not blockers
            else ""
        ),
        "registration_schema_version": (
            str(document.get("schema_version") or "")
            if isinstance(document, dict) and not blockers
            else ""
        ),
        "uncertainty_policy_hash": (
            str(document.get("uncertainty_policy_hash") or "")
            if isinstance(document, dict) and not blockers
            else ""
        ),
        "target_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _safe_protocol_verification(protocol: Any) -> dict[str, Any]:
    try:
        return verify_strategy_matrix_protocol(
            protocol,
            enforce_not_expired=False,
            verify_current_implementation=False,
        )
    except Exception:
        return {"status": "BLOCK", "blockers": ["protocol_verification_failed"]}


def _safe_gate_verification(replayed_gate: Any) -> dict[str, Any]:
    try:
        return verify_replayed_correlation_cluster_gate(replayed_gate)
    except Exception:
        return {"status": "BLOCK", "blockers": ["gate_verification_failed"]}


def _safe_bound_artifact_verification(protocol: Any) -> dict[str, Any]:
    try:
        return verify_bound_strategy_research_protocol_artifact(protocol)
    except Exception:
        return {"status": "BLOCK", "blockers": ["artifact_verification_failed"]}


def assess_strategy_correlation_protocol_binding(
    protocol: Any,
    registration: Any,
    replayed_gate: Any,
    uncertainty_audit: Any | None = None,
) -> dict[str, Any]:
    registration_verification = verify_strategy_correlation_protocol_registration(registration)
    gate_verification = _safe_gate_verification(replayed_gate)
    protocol_verification = _safe_protocol_verification(protocol)
    artifact_verification = _safe_bound_artifact_verification(protocol)
    registration_map = _mapping(registration)
    registration_schema = str(registration_map.get("schema_version") or "")
    uncertainty_required = (
        registration_schema == STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2
    )
    uncertainty_verification = (
        verify_strategy_correlation_uncertainty_audit(uncertainty_audit)
        if uncertainty_required
        else {"status": "NOT_REQUIRED", "blockers": []}
    )
    protocol_map = _mapping(protocol)
    gate_map = _mapping(replayed_gate)
    matrix_replay = _mapping(gate_map.get("matrix_replay"))
    gate_preregistration = _mapping(matrix_replay.get("preregistration"))
    completed_price_input = _mapping(matrix_replay.get("completed_price_input"))

    registration_valid = registration_verification.get("status") == "PASS"
    gate_valid = gate_verification.get("status") == "PASS"
    protocol_valid = protocol_verification.get("status") == "PASS"
    artifact_valid = artifact_verification.get("status") == "PASS"
    local_cluster_match = registration_valid and gate_valid and (
        str(gate_preregistration.get("preregistration_hash") or "")
        == str(_mapping(registration_map.get("preregistration")).get("preregistration_hash") or "")
    )
    local_cutoff_match = registration_valid and gate_valid and (
        completed_price_input.get("cutoff_date") == registration_map.get("cutoff_date")
    )
    local_alignment_match = registration_valid and gate_valid and (
        completed_price_input.get("selection_alignment_input_hash")
        == registration_map.get("selection_alignment_input_hash")
    )
    gate_identity = (
        gate_map.get("strategy_id"),
        gate_map.get("variant_id"),
        gate_map.get("lane"),
    )
    registered_identities = {
        (item.get("strategy_id"), item.get("variant_id"), item.get("lane"))
        for item in registration_map.get("evaluations", [])
        if isinstance(item, dict)
    }
    local_evaluation_match = registration_valid and gate_valid and gate_identity in registered_identities
    base_local_chain_reverified = all((
        registration_valid,
        gate_valid,
        local_cluster_match,
        local_cutoff_match,
        local_alignment_match,
        local_evaluation_match,
    ))
    uncertainty_map = _mapping(uncertainty_audit)
    local_uncertainty_matrix_match = uncertainty_required and (
        uncertainty_map.get("matrix_replay") == gate_map.get("matrix_replay")
    )
    local_uncertainty_policy_match = uncertainty_required and (
        uncertainty_map.get("policy_hash") == registration_map.get("uncertainty_policy_hash")
    )
    local_uncertainty_audit_bound = all((
        uncertainty_required,
        uncertainty_verification.get("status") == "PASS",
        local_uncertainty_matrix_match,
        local_uncertainty_policy_match,
    ))
    local_chain_reverified = base_local_chain_reverified and (
        local_uncertainty_audit_bound if uncertainty_required else True
    )
    gate_decision_status = str(gate_map.get("status") or "UNKNOWN")
    uncertainty_decision_status = (
        str(uncertainty_map.get("status") or "UNKNOWN")
        if uncertainty_required else "NOT_REQUIRED"
    )
    decision_disposition = _strategy_correlation_decision_disposition(
        gate_decision_status=gate_decision_status,
        uncertainty_decision_status=uncertainty_decision_status,
    )
    local_decision_status = str(decision_disposition["status"])

    protocol_schema = str(protocol_map.get("schema_version") or "")
    batch_spec = _mapping(protocol_map.get("batch_spec"))
    observed_report_schema = batch_spec.get("report_schema_version")
    if isinstance(observed_report_schema, bool) or not isinstance(observed_report_schema, int):
        observed_report_schema = None
    embedded_registration = protocol_map.get("correlation_cluster_protocol_registration")
    embedded_registration_hash = protocol_map.get(
        "correlation_cluster_protocol_registration_hash"
    )
    protocol_registration_hash_bound = (
        protocol_schema == TARGET_PROTOCOL_SCHEMA_VERSION
        and embedded_registration == registration
        and embedded_registration_hash == registration_map.get("registration_hash")
    )
    immutable_protocol_artifact_bound = all((
        local_chain_reverified,
        protocol_valid,
        protocol_registration_hash_bound,
        artifact_valid,
    ))
    formal_registry_bound = False
    current_report_schema_bound = False
    formal_binding_complete = False

    blockers: list[str] = []
    blockers.extend(
        f"registration:{item}"
        for item in registration_verification.get("blockers") or []
    )
    blockers.extend(f"gate:{item}" for item in gate_verification.get("blockers") or [])
    blockers.extend(
        f"protocol:{item}" for item in protocol_verification.get("blockers") or []
    )
    blockers.extend(
        f"artifact:{item}" for item in artifact_verification.get("blockers") or []
    )
    blockers.extend(
        f"uncertainty:{item}" for item in uncertainty_verification.get("blockers") or []
    )
    if registration_valid and gate_valid and not local_cluster_match:
        blockers.append("local_cluster_preregistration_mismatch")
    if registration_valid and gate_valid and not local_cutoff_match:
        blockers.append("local_preregistered_cutoff_mismatch")
    if registration_valid and gate_valid and not local_alignment_match:
        blockers.append("local_selection_alignment_input_mismatch")
    if registration_valid and gate_valid and not local_evaluation_match:
        blockers.append("local_evaluation_not_preregistered")
    if uncertainty_required and not local_uncertainty_matrix_match:
        blockers.append("local_uncertainty_matrix_replay_mismatch")
    if uncertainty_required and not local_uncertainty_policy_match:
        blockers.append("local_uncertainty_policy_mismatch")
    decision_blocker = decision_disposition["blocker"]
    if decision_blocker is not None:
        blockers.append(str(decision_blocker))
    if protocol_schema != TARGET_PROTOCOL_SCHEMA_VERSION:
        blockers.append("strategy_matrix_protocol_v4_required")
    if not protocol_registration_hash_bound:
        blockers.append("protocol_registration_hash_not_bound")
    if observed_report_schema != TARGET_REPORT_SCHEMA_VERSION:
        blockers.append("strategy_research_report_schema_15_required")
    if immutable_protocol_artifact_bound:
        blockers.append("strategy_matrix_protocol_v4_registry_transaction_required")
    blockers = list(dict.fromkeys(blockers))

    if not base_local_chain_reverified:
        next_evidence = "VALID_LOCAL_REPLAY_CHAIN"
    elif registration_schema != STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2:
        next_evidence = "CORRELATION_PROTOCOL_REGISTRATION_V2"
    elif not local_uncertainty_audit_bound:
        next_evidence = "VALID_PREREGISTERED_UNCERTAINTY_AUDIT"
    elif decision_disposition["next_evidence_required"] is not None:
        next_evidence = str(decision_disposition["next_evidence_required"])
    elif protocol_schema != TARGET_PROTOCOL_SCHEMA_VERSION:
        next_evidence = "STRATEGY_MATRIX_PROTOCOL_V4"
    elif not protocol_valid:
        next_evidence = "VALID_BOUND_PROTOCOL_V4"
    elif not protocol_registration_hash_bound:
        next_evidence = "PROTOCOL_REGISTRATION_HASH_BINDING"
    elif not artifact_valid:
        next_evidence = "IMMUTABLE_PROTOCOL_V4_ARTIFACT"
    else:
        next_evidence = "PROTOCOL_V4_REGISTRY_TRANSACTION"

    payload: dict[str, Any] = {
        "schema_version": STRATEGY_CORRELATION_PROTOCOL_BINDING_ASSESSMENT_SCHEMA_VERSION,
        "status": "PASS" if formal_binding_complete else "BLOCK",
        "local_chain_status": "PASS" if local_chain_reverified else "BLOCK",
        "local_decision_status": local_decision_status,
        "protocol_status": "PASS" if protocol_valid else "BLOCK",
        "protocol_artifact_status": "PASS" if artifact_valid else "BLOCK",
        "gate_decision_status": gate_decision_status,
        "uncertainty_audit_status": (
            "PASS" if uncertainty_verification.get("status") == "PASS" else (
                "NOT_REQUIRED" if not uncertainty_required else "BLOCK"
            )
        ),
        "uncertainty_decision_status": uncertainty_decision_status,
        "required_protocol_schema_version": TARGET_PROTOCOL_SCHEMA_VERSION,
        "observed_protocol_schema_version": protocol_schema or "UNKNOWN",
        "target_report_schema_version": TARGET_REPORT_SCHEMA_VERSION,
        "observed_report_schema_version": observed_report_schema,
        "registration_hash": (
            str(registration_map.get("registration_hash") or "")
            if registration_valid else ""
        ),
        "protocol_hash": str(protocol_map.get("protocol_hash") or ""),
        "replayed_gate_evaluation_hash": str(gate_map.get("evaluation_hash") or ""),
        "local_cluster_preregistration_match": local_cluster_match,
        "local_preregistered_cutoff_match": local_cutoff_match,
        "local_selection_alignment_input_match": local_alignment_match,
        "local_evaluation_match": local_evaluation_match,
        "local_uncertainty_matrix_match": local_uncertainty_matrix_match,
        "local_uncertainty_policy_match": local_uncertainty_policy_match,
        "local_uncertainty_audit_bound": local_uncertainty_audit_bound,
        "local_chain_reverified": local_chain_reverified,
        "protocol_registration_hash_bound": protocol_registration_hash_bound,
        "immutable_protocol_artifact_bound": immutable_protocol_artifact_bound,
        "preregistered_cutoff_bound": False,
        "formal_registry_bound": formal_registry_bound,
        "current_report_schema_bound": current_report_schema_bound,
        "full_manifest_reverified": False,
        "external_authenticity_proven": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "next_evidence_required": next_evidence,
        "blockers": blockers,
    }
    payload["assessment_hash"] = canonical_hash(payload)
    return payload


def verify_strategy_correlation_protocol_binding_assessment(
    document: Any,
    *,
    protocol: Any,
    registration: Any,
    replayed_gate: Any,
    uncertainty_audit: Any | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(document, dict):
        blockers.append("strategy_correlation_binding_assessment_type_invalid")
    expected = assess_strategy_correlation_protocol_binding(
        protocol,
        registration,
        replayed_gate,
        uncertainty_audit,
    )
    if not strict_json_contract_equal(document, expected):
        blockers.append("strategy_correlation_binding_assessment_replay_mismatch")
    if authority_violations(document):
        blockers.append("strategy_correlation_binding_assessment_authority_violation")
    return {
        "schema_version": STRATEGY_CORRELATION_PROTOCOL_BINDING_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "assessment_hash": expected["assessment_hash"] if not blockers else "",
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "STRATEGY_CORRELATION_PROTOCOL_BINDING_ASSESSMENT_SCHEMA_VERSION",
    "STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION",
    "STRATEGY_CORRELATION_PROTOCOL_REGISTRATION_SCHEMA_VERSION_V2",
    "TARGET_PROTOCOL_SCHEMA_VERSION",
    "TARGET_REPORT_SCHEMA_VERSION",
    "assess_strategy_correlation_protocol_binding",
    "build_strategy_correlation_protocol_registration",
    "build_strategy_correlation_protocol_registration_v2",
    "verify_strategy_correlation_protocol_binding_assessment",
    "verify_strategy_correlation_protocol_registration",
]
def _strategy_correlation_decision_disposition(
    *,
    gate_decision_status: str,
    uncertainty_decision_status: str,
) -> dict[str, str | None]:
    if gate_decision_status != "PASS":
        return {
            "status": "BLOCK",
            "blocker": "local_correlation_gate_decision_block",
            "next_evidence_required": "CORRELATION_GATE_DECISION_BLOCK_OR_REREGISTER",
        }
    if uncertainty_decision_status not in {"PASS", "NOT_REQUIRED"}:
        return {
            "status": "BLOCK",
            "blocker": "local_uncertainty_decision_block",
            "next_evidence_required": "RESOLVE_CORRELATION_UNCERTAINTY_OR_REREGISTER",
        }
    return {
        "status": "PASS",
        "blocker": None,
        "next_evidence_required": None,
    }
