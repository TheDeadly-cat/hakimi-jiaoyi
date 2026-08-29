from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3 as preregistration_contract,
)
from exchange_terminal.services import (
    strategy_correlation_provider_dataset_content_issuance_replay_gate_v1 as content_replay_contract,
)
from exchange_terminal.services.execution_authority import authority_violations


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-"
    "shadow-input-readiness-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-shadow-input-readiness-envelope-1"
)
STATUS = "UNKNOWN"
POSITIVE_SOURCE_STATE = "LOCAL_SOURCE_CHAIN_VERIFIED"
UNKNOWN_SOURCE_STATE = "UNKNOWN"
POSITIVE_GAP_STATE = "REQUIRED_PORTFOLIO_INPUTS_NOT_SUPPLIED"
UNKNOWN_GAP_STATE = "SOURCE_CONTRACT_UNVERIFIED"
POSITIVE_MATURITY_STATE = "PARTIAL_LOCAL_EVIDENCE"
UNKNOWN_MATURITY_STATE = "UNKNOWN"
PERMISSION_STATE = "DENIED"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PREREGISTRATION_CONTEXT_KEYS = {
    "preregistration_v2",
    "v2_verification_context",
    "current_implementation_sha256",
}
_CONTENT_REPLAY_CONTEXT_KEYS = {
    "attestation_document",
    "attestation_context",
    "lifecycle_replay_document",
    "lifecycle_replay_context",
    "replay_registration",
    "pinned_checkpoint",
    "checkpoint",
    "inclusion_proof",
    "consistency_proof",
    "occurrence_audit",
    "expected_registration_hash",
    "expected_pinned_checkpoint_hash",
    "expected_checkpoint_hash",
    "expected_occurrence_audit_hash",
    "reference_time_utc",
}
_LOCALLY_VERIFIED_INPUT_NAMES = {
    "provider_dataset_content_attestation_verification",
    "provider_dataset_key_lifecycle_replay_verification",
    "provider_dataset_content_issuance_replay_registration",
    "provider_dataset_content_issuance_replay_pinned_checkpoint",
    "provider_dataset_content_issuance_replay_checkpoint",
    "provider_dataset_content_issuance_replay_occurrence_audit",
    "provider_dataset_content_issuance_replay_verification",
}
_EXPECTED_NOT_SUPPLIED_INPUT_NAMES = {
    "dual_source_receipt",
    "portfolio_risk_adapter",
    "legacy_matrix_derivation_binding",
    "native_cutoff_manifest",
    "session_freshness_registration",
    "session_freshness_evaluation",
}
_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _authority_invalid(value: Any) -> bool:
    try:
        return bool(authority_violations(value))
    except (MemoryError, RecursionError, TypeError, ValueError):
        return True


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "shadow_consumer_execution_allowed": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_claim_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "preregistration_v3_verified": False,
        "content_issuance_replay_gate_verified": False,
        "content_attestation_source_reverified": False,
        "dataset_key_lifecycle_replay_source_reverified": False,
        "content_issuance_registration_verified": False,
        "content_issuance_checkpoint_verified": False,
        "content_issuance_occurrence_audit_verified": False,
        "required_portfolio_input_set_complete": False,
        "external_provider_key_control_verified": False,
        "external_provider_data_issuance_verified": False,
        "external_content_replay_registry_authority_verified": False,
        "external_occurrence_auditor_authority_verified": False,
        "durable_content_checkpoint_publication_verified": False,
        "external_time_authority_authenticated": False,
        "runtime_consumption_replay_enforcement_verified": False,
        "future_replay_absence_verified": False,
        "shadow_consumer_executed": False,
        "risk_service_invoked": False,
        "ui_mounted": False,
        "profitability_verified": False,
    }


def _sealed(
    *,
    source_state: str,
    gap_state: str,
    maturity_state: str,
    input_inventory: list[dict[str, Any]],
    source_lineage: dict[str, Any],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    verified_count = sum(
        entry["state"] == "VERIFIED"
        for entry in input_inventory
    )
    not_supplied_count = sum(
        entry["state"] == "NOT_SUPPLIED"
        for entry in input_inventory
    )
    unverified_count = sum(
        entry["state"] == "UNVERIFIED"
        for entry in input_inventory
    )
    body = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "source_state": source_state,
        "gap_state": gap_state,
        "maturity_state": maturity_state,
        "permission_state": PERMISSION_STATE,
        "axes": {
            "source": source_state,
            "gap": gap_state,
            "maturity": maturity_state,
            "permission": PERMISSION_STATE,
        },
        "summary": {
            "required_input_count": len(input_inventory),
            "verified_input_count": verified_count,
            "not_supplied_input_count": not_supplied_count,
            "unverified_input_count": unverified_count,
        },
        "input_inventory": input_inventory,
        "source_lineage": source_lineage,
        "facts": facts,
        "blockers": blockers,
        "authority": _authority(),
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "envelope_hash": _sha256(body)}


def _unknown(reason: str) -> dict[str, Any]:
    facts = _facts()
    return _sealed(
        source_state=UNKNOWN_SOURCE_STATE,
        gap_state=UNKNOWN_GAP_STATE,
        maturity_state=UNKNOWN_MATURITY_STATE,
        input_inventory=[],
        source_lineage={
            "preregistration_v3_hash": None,
            "content_issuance_replay_verification_hash": None,
            "future_evaluation_id_hash": None,
            "source_attestation_hash": None,
            "checkpoint_hash": None,
            "occurrence_audit_hash": None,
        },
        facts=facts,
        blockers=[
            reason,
            "shadow_input_readiness_unknown",
            "shadow_consumer_not_executed",
            "risk_service_not_invoked",
            "current_admission_denied",
        ],
    )


def _required_inventory(
    preregistration_v3: dict[str, Any],
) -> list[dict[str, Any]] | None:
    required = preregistration_v3.get("required_shadow_input_schemas")
    if type(required) is not list:
        return None
    inventory: list[dict[str, Any]] = []
    names: list[str] = []
    for entry in required:
        if (
            type(entry) is not dict
            or set(entry) != {"input", "schema_version"}
            or type(entry.get("input")) is not str
            or not entry["input"]
            or type(entry.get("schema_version")) is not str
            or not entry["schema_version"]
        ):
            return None
        name = entry["input"]
        names.append(name)
        state = (
            "VERIFIED"
            if name in _LOCALLY_VERIFIED_INPUT_NAMES
            else "NOT_SUPPLIED"
        )
        inventory.append(
            {
                "input": name,
                "schema_version": entry["schema_version"],
                "state": state,
            }
        )
    name_set = set(names)
    if (
        len(names) != len(name_set)
        or name_set
        != _LOCALLY_VERIFIED_INPUT_NAMES
        | _EXPECTED_NOT_SUPPLIED_INPUT_NAMES
    ):
        return None
    return inventory


def build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1(
    preregistration_v3: Any,
    content_issuance_replay_verification: Any,
    *,
    preregistration_verification_context: Any,
    content_issuance_replay_verification_context: Any,
) -> dict[str, Any]:
    if (
        type(preregistration_verification_context) is not dict
        or set(preregistration_verification_context)
        != _PREREGISTRATION_CONTEXT_KEYS
        or type(content_issuance_replay_verification_context) is not dict
        or set(content_issuance_replay_verification_context)
        != _CONTENT_REPLAY_CONTEXT_KEYS
        or _authority_invalid(
            [
                preregistration_v3,
                content_issuance_replay_verification,
                preregistration_verification_context,
                content_issuance_replay_verification_context,
            ]
        )
    ):
        return _unknown("SOURCE_CONTEXT_INVALID")
    try:
        preregistration_verification = preregistration_contract.verify_strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v3(
            preregistration_v3,
            **preregistration_verification_context,
        )
        replay_verified = content_replay_contract.verify_provider_dataset_content_issuance_replay_gate_v1(
            content_issuance_replay_verification,
            **content_issuance_replay_verification_context,
        )
    except Exception:
        return _unknown("SOURCE_VERIFIER_ERROR")
    if (
        type(preregistration_verification) is not dict
        or preregistration_verification.get("status") != "PASS"
        or preregistration_verification.get(
            "preregistration_exactly_verified"
        )
        is not True
        or preregistration_verification.get("preregistration_status")
        != "BLOCKED"
        or preregistration_verification.get("blockers") != []
        or preregistration_verification.get(
            "shadow_consumer_activation_allowed"
        )
        is not False
        or preregistration_verification.get(
            "runtime_gate_activation_allowed"
        )
        is not False
        or replay_verified is not True
    ):
        return _unknown("SOURCE_CONTRACT_UNVERIFIED")
    if (
        type(preregistration_v3) is not dict
        or preregistration_v3.get("schema_version")
        != preregistration_contract.PREREGISTRATION_SCHEMA_VERSION
        or preregistration_v3.get("static_fingerprint")
        != preregistration_contract.STATIC_FINGERPRINT
        or preregistration_v3.get("status") != "BLOCKED"
        or preregistration_v3.get("authority", {}).get(
            "shadow_consumer_activation_allowed"
        )
        is not False
        or preregistration_v3.get("facts", {}).get(
            "content_issuance_replay_evidence_bound"
        )
        is not False
        or type(content_issuance_replay_verification) is not dict
        or content_issuance_replay_verification.get("schema_version")
        != content_replay_contract.SCHEMA_VERSION
        or content_issuance_replay_verification.get("static_fingerprint")
        != content_replay_contract.STATIC_FINGERPRINT
        or content_issuance_replay_verification.get("status") != "PASS"
        or content_issuance_replay_verification.get("verification_state")
        != content_replay_contract.VERIFICATION_STATE
        or content_issuance_replay_verification.get("permissions")
        != _PERMISSIONS
        or content_issuance_replay_verification.get(
            "current_writer_activation_allowed"
        )
        is not False
        or content_issuance_replay_verification.get(
            "current_admission_allowed"
        )
        is not False
        or content_issuance_replay_verification.get("facts", {}).get(
            "external_provider_data_issuance_verified"
        )
        is not False
        or content_issuance_replay_verification.get("facts", {}).get(
            "runtime_consumption_replay_enforcement_verified"
        )
        is not False
        or not _valid_sha256(
            content_issuance_replay_verification.get("verification_hash")
        )
        or not _valid_sha256(
            content_issuance_replay_verification.get(
                "future_evaluation_id_hash"
            )
        )
    ):
        return _unknown("SOURCE_CONTRACT_MISMATCH")
    inventory = _required_inventory(preregistration_v3)
    if inventory is None:
        return _unknown("REQUIRED_INPUT_CONTRACT_INVALID")

    facts = _facts()
    facts.update(
        {
            "preregistration_v3_verified": True,
            "content_issuance_replay_gate_verified": True,
            "content_attestation_source_reverified": True,
            "dataset_key_lifecycle_replay_source_reverified": True,
            "content_issuance_registration_verified": True,
            "content_issuance_checkpoint_verified": True,
            "content_issuance_occurrence_audit_verified": True,
        }
    )
    missing_names = [
        entry["input"]
        for entry in inventory
        if entry["state"] == "NOT_SUPPLIED"
    ]
    blockers = [
        f"required_input_not_supplied:{name}"
        for name in missing_names
    ] + [
        "external_provider_key_control_unproven",
        "external_provider_data_issuance_unproven",
        "external_content_replay_registry_authority_unproven",
        "external_occurrence_auditor_authority_unproven",
        "durable_content_checkpoint_publication_unproven",
        "external_time_authority_unauthenticated",
        "runtime_consumption_replay_enforcement_missing",
        "future_replay_absence_unproven",
        "shadow_consumer_not_executed",
        "risk_service_input_not_versioned",
        "risk_service_not_invoked",
        "current_admission_denied",
    ]
    return _sealed(
        source_state=POSITIVE_SOURCE_STATE,
        gap_state=POSITIVE_GAP_STATE,
        maturity_state=POSITIVE_MATURITY_STATE,
        input_inventory=inventory,
        source_lineage={
            "preregistration_v3_hash": preregistration_v3[
                "preregistration_hash"
            ],
            "content_issuance_replay_verification_hash": (
                content_issuance_replay_verification["verification_hash"]
            ),
            "future_evaluation_id_hash": (
                content_issuance_replay_verification[
                    "future_evaluation_id_hash"
                ]
            ),
            "source_attestation_hash": (
                content_issuance_replay_verification[
                    "source_attestation_hash"
                ]
            ),
            "checkpoint_hash": content_issuance_replay_verification[
                "checkpoint_hash"
            ],
            "occurrence_audit_hash": (
                content_issuance_replay_verification[
                    "occurrence_audit_hash"
                ]
            ),
        },
        facts=facts,
        blockers=blockers,
    )


def verify_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1(
    document: Any,
    preregistration_v3: Any,
    content_issuance_replay_verification: Any,
    *,
    preregistration_verification_context: Any,
    content_issuance_replay_verification_context: Any,
) -> bool:
    if type(document) is not dict or _authority_invalid(document):
        return False
    try:
        rebuilt = build_strategy_correlation_cluster_portfolio_risk_shadow_input_readiness_envelope_v1(
            preregistration_v3,
            content_issuance_replay_verification,
            preregistration_verification_context=(
                preregistration_verification_context
            ),
            content_issuance_replay_verification_context=(
                content_issuance_replay_verification_context
            ),
        )
    except Exception:
        return False
    return document == rebuilt
