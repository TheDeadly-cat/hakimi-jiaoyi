from __future__ import annotations

from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1
    as issuance_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-risk-downside-tail-post-registration-execution-issuance-"
    "preregistration-verification-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20260823-receipt-v5-issuance-preregistration-python-envelope-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
ISSUANCE_PREREGISTRATION_V1_IMPLEMENTATION_SHA256 = (
    "76a1c05a55395c3258869336b0d00b8e1613670befea35f6152be6947016e6ce"
)
STAGE_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
_ALLOWED_SEMANTIC_STATES = {"CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"}
_UNDERLYING_AUTHORITY = {
    "descriptive_only": True,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "formal_registration_activation_allowed": False,
    "live_order_allowed": False,
    "migration_allowed": False,
    "paper_authorized": False,
    "presentation_consumer_activation_allowed": False,
    "presentation_mount_allowed": False,
    "post_registration_receipt_issuance_allowed": False,
    "runtime_gate_activation_allowed": False,
    "shadow_consumer_activation_allowed": False,
    "writer_allowed": False,
}
_AUTHORITY = {
    **_UNDERLYING_AUTHORITY,
    "witness_candidate_activation_allowed": False,
}


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sealed_exact(document: Any, hash_field: str) -> bool:
    if not isinstance(document, dict) or not _is_hash(document.get(hash_field)):
        return False
    try:
        expected = seal_strict_canonical_document(document, hash_field)
    except (TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def _exact_dict(actual: Any, expected: dict[str, Any]) -> bool:
    return isinstance(actual, dict) and strict_json_contract_equal(
        actual,
        expected,
    )


def _verify_underlying(
    preregistration_document: Any,
    registration_v7_document: Any,
    registration_v7_manifest: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
    issuance_id: Any,
    nonce_commitment_sha256: Any,
) -> dict[str, Any]:
    try:
        return issuance_v1.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
            preregistration_document,
            registration_v7_document,
            registration_v7_manifest,
            execution_evidence_v4_document,
            receipt_v4_document,
            receipt_v4_verification_document,
            projection_v6_document,
            execution_preregistration_v1_document,
            issuance_id,
            nonce_commitment_sha256,
        )
    except (TypeError, ValueError):
        return {"status": "BLOCK", "execution_semantic_state": "UNVERIFIED"}


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1(
    preregistration_document: Any,
    registration_v7_document: Any,
    registration_v7_manifest: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
    issuance_id: Any,
    nonce_commitment_sha256: Any,
) -> dict[str, Any]:
    underlying_verification = _verify_underlying(
        preregistration_document,
        registration_v7_document,
        registration_v7_manifest,
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
        issuance_id,
        nonce_commitment_sha256,
    )
    preregistration_sealed = _sealed_exact(
        preregistration_document,
        "preregistration_hash",
    )
    preregistration_identity_exact = bool(
        isinstance(preregistration_document, dict)
        and preregistration_document.get("schema_version")
        == issuance_v1.SCHEMA_VERSION
        and preregistration_document.get("static_fingerprint")
        == issuance_v1.STATIC_FINGERPRINT
        and preregistration_document.get("status") == "BLOCKED"
    )
    underlying_exact = bool(
        underlying_verification.get("status") == "PASS"
        and underlying_verification.get("preregistration_status") == "BLOCKED"
        and underlying_verification.get("local_preregistration_complete")
        is True
        and _is_hash(underlying_verification.get("preregistration_hash"))
        and _is_hash(underlying_verification.get("scope_hash"))
    )
    semantic_state = underlying_verification.get(
        "execution_semantic_state",
        "UNVERIFIED",
    )
    semantic_state_exact = semantic_state in _ALLOWED_SEMANTIC_STATES

    source = (
        preregistration_document.get("source", {})
        if isinstance(preregistration_document, dict)
        else {}
    )
    issuance = (
        preregistration_document.get("issuance", {})
        if isinstance(preregistration_document, dict)
        else {}
    )
    anti_replay = (
        preregistration_document.get("anti_replay", {})
        if isinstance(preregistration_document, dict)
        else {}
    )
    facts = (
        preregistration_document.get("facts", {})
        if isinstance(preregistration_document, dict)
        else {}
    )
    authority_locked = bool(
        isinstance(preregistration_document, dict)
        and _exact_dict(
            preregistration_document.get("authority"),
            _UNDERLYING_AUTHORITY,
        )
    )
    registration_hash_bound = bool(
        isinstance(registration_v7_document, dict)
        and _is_hash(source.get("registration_v7_hash"))
        and source.get("registration_v7_hash")
        == registration_v7_document.get("registration_hash")
        and issuance.get("registration_hash")
        == registration_v7_document.get("registration_hash")
    )
    evidence_hash_bound = bool(
        isinstance(execution_evidence_v4_document, dict)
        and _is_hash(source.get("execution_evidence_v4_hash"))
        and source.get("execution_evidence_v4_hash")
        == execution_evidence_v4_document.get("evidence_hash")
        and issuance.get("execution_evidence_hash")
        == execution_evidence_v4_document.get("evidence_hash")
    )
    receipt_hash_bound = bool(
        isinstance(receipt_v4_document, dict)
        and _is_hash(source.get("pre_registration_receipt_v4_hash"))
        and source.get("pre_registration_receipt_v4_hash")
        == receipt_v4_document.get("receipt_hash")
        and issuance.get("pre_registration_receipt_hash")
        == receipt_v4_document.get("receipt_hash")
    )
    projection_hash_bound = bool(
        isinstance(projection_v6_document, dict)
        and _is_hash(source.get("projection_v6_hash"))
        and source.get("projection_v6_hash")
        == projection_v6_document.get("projection_hash")
    )
    execution_preregistration_hash_bound = bool(
        isinstance(execution_preregistration_v1_document, dict)
        and _is_hash(source.get("execution_preregistration_v1_hash"))
        and source.get("execution_preregistration_v1_hash")
        == execution_preregistration_v1_document.get("preregistration_hash")
    )
    issuance_scope_bound = bool(
        issuance.get("issuance_id") == issuance_id
        and issuance.get("issuance_sequence") == 1
        and anti_replay.get("nonce_commitment_sha256")
        == nonce_commitment_sha256
        and _is_hash(anti_replay.get("scope_hash"))
        and anti_replay.get("scope_hash")
        == underlying_verification.get("scope_hash")
    )
    target_schemas_exact = bool(
        issuance.get("target_receipt_schema_version")
        == issuance_v1.TARGET_RECEIPT_SCHEMA_VERSION
        and issuance.get("target_receipt_static_fingerprint")
        == issuance_v1.TARGET_RECEIPT_STATIC_FINGERPRINT
        and issuance.get("target_witness_policy_schema_version")
        == issuance_v1.TARGET_WITNESS_POLICY_SCHEMA_VERSION
        and issuance.get("target_challenge_schema_version")
        == issuance_v1.TARGET_CHALLENGE_SCHEMA_VERSION
        and issuance.get("target_attestation_schema_version")
        == issuance_v1.TARGET_ATTESTATION_SCHEMA_VERSION
        and issuance.get("target_witness_verification_schema_version")
        == issuance_v1.TARGET_WITNESS_VERIFICATION_SCHEMA_VERSION
        and issuance.get("target_anti_replay_consumption_schema_version")
        == issuance_v1.TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION
    )
    anti_replay_unbound_exact = bool(
        anti_replay.get("namespace") == issuance_v1.ANTI_REPLAY_NAMESPACE
        and anti_replay.get("registry_consistency_required") == "LINEARIZABLE"
        and anti_replay.get("required_registry_operation")
        == "ATOMIC_PUT_IF_ABSENT_THEN_CONSUME_ONCE"
        and anti_replay.get("challenge_use_limit") == 1
        and anti_replay.get("receipt_issue_limit") == 1
        and anti_replay.get("nonce_material_embedded") is False
        and anti_replay.get("external_registry_snapshot_hash") is None
        and anti_replay.get("nonce_consumption_receipt_hash") is None
        and anti_replay.get("registry_bound") is False
        and anti_replay.get("atomic_consumption_verified") is False
        and anti_replay.get("duplicate_rejection_verified") is False
        and anti_replay.get("trusted_time_source_bound") is False
        and facts.get("raw_nonce_received") is False
        and facts.get("post_registration_receipt_issued") is False
    )

    checks = [
        {
            "name": "issuance_preregistration_v1_strict_canonical_seal_exact",
            "ok": preregistration_sealed,
            "blocking": True,
        },
        {
            "name": "issuance_preregistration_v1_identity_blocked_exact",
            "ok": preregistration_identity_exact,
            "blocking": True,
        },
        {
            "name": "issuance_preregistration_v1_public_verifier_pass",
            "ok": underlying_exact,
            "blocking": True,
        },
        {
            "name": "execution_semantic_state_exact",
            "ok": semantic_state_exact,
            "blocking": True,
        },
        {
            "name": "registration_v7_hash_edge_exact",
            "ok": registration_hash_bound,
            "blocking": True,
        },
        {
            "name": "execution_evidence_v4_hash_edge_exact",
            "ok": evidence_hash_bound,
            "blocking": True,
        },
        {
            "name": "pre_registration_receipt_v4_hash_edge_exact",
            "ok": receipt_hash_bound,
            "blocking": True,
        },
        {
            "name": "projection_v6_hash_edge_exact",
            "ok": projection_hash_bound,
            "blocking": True,
        },
        {
            "name": "execution_preregistration_v1_hash_edge_exact",
            "ok": execution_preregistration_hash_bound,
            "blocking": True,
        },
        {
            "name": "issuance_id_commitment_and_scope_hash_bound",
            "ok": issuance_scope_bound,
            "blocking": True,
        },
        {
            "name": "future_target_schemas_exact",
            "ok": target_schemas_exact,
            "blocking": True,
        },
        {
            "name": "anti_replay_registry_remains_explicitly_unbound",
            "ok": anti_replay_unbound_exact,
            "blocking": True,
        },
        {
            "name": "issuance_preregistration_authority_locked",
            "ok": authority_locked,
            "blocking": True,
        },
    ]
    blockers = [
        check["name"] for check in checks if check.get("ok") is not True
    ]
    passed = not blockers

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if passed else "BLOCK",
        "decision": (
            "BLOCKED_ISSUANCE_PREREGISTRATION_V1_EXACTLY_VERIFIED_FOR_"
            "CROSS_RUNTIME_WITNESS_CONSUMER"
            if passed
            else "ISSUANCE_PREREGISTRATION_V1_VERIFICATION_ENVELOPE_BLOCKED"
        ),
        "source": {
            "issuance_preregistration_schema_version": (
                issuance_v1.SCHEMA_VERSION
                if preregistration_identity_exact
                else "UNKNOWN"
            ),
            "issuance_preregistration_static_fingerprint": (
                issuance_v1.STATIC_FINGERPRINT
                if preregistration_identity_exact
                else "UNKNOWN"
            ),
            "issuance_preregistration_hash": (
                preregistration_document.get("preregistration_hash")
                if preregistration_sealed
                else None
            ),
            "issuance_preregistration_implementation_sha256": (
                ISSUANCE_PREREGISTRATION_V1_IMPLEMENTATION_SHA256
            ),
            "registration_v7_hash": (
                source.get("registration_v7_hash")
                if registration_hash_bound
                else None
            ),
            "execution_evidence_v4_hash": (
                source.get("execution_evidence_v4_hash")
                if evidence_hash_bound
                else None
            ),
            "pre_registration_receipt_v4_hash": (
                source.get("pre_registration_receipt_v4_hash")
                if receipt_hash_bound
                else None
            ),
            "projection_v6_hash": (
                source.get("projection_v6_hash")
                if projection_hash_bound
                else None
            ),
            "execution_preregistration_v1_hash": (
                source.get("execution_preregistration_v1_hash")
                if execution_preregistration_hash_bound
                else None
            ),
            "execution_semantic_state": (
                semantic_state if semantic_state_exact else "UNVERIFIED"
            ),
            "issuance_id": (
                issuance.get("issuance_id") if issuance_scope_bound else "UNKNOWN"
            ),
            "nonce_commitment_sha256": (
                anti_replay.get("nonce_commitment_sha256")
                if issuance_scope_bound
                else None
            ),
            "anti_replay_scope_hash": (
                anti_replay.get("scope_hash") if issuance_scope_bound else None
            ),
            "verification_environment": "PYTHON_CONTRACT_PROCESS",
        },
        "target_contracts": {
            "receipt_schema_version": issuance_v1.TARGET_RECEIPT_SCHEMA_VERSION,
            "receipt_static_fingerprint": (
                issuance_v1.TARGET_RECEIPT_STATIC_FINGERPRINT
            ),
            "witness_policy_schema_version": (
                issuance_v1.TARGET_WITNESS_POLICY_SCHEMA_VERSION
            ),
            "challenge_schema_version": (
                issuance_v1.TARGET_CHALLENGE_SCHEMA_VERSION
            ),
            "attestation_schema_version": (
                issuance_v1.TARGET_ATTESTATION_SCHEMA_VERSION
            ),
            "witness_verification_schema_version": (
                issuance_v1.TARGET_WITNESS_VERIFICATION_SCHEMA_VERSION
            ),
            "anti_replay_consumption_schema_version": (
                issuance_v1.TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION
            ),
        },
        "verification": {
            "underlying_public_verifier_status": (
                underlying_verification.get("status", "BLOCK")
            ),
            "underlying_preregistration_status": (
                underlying_verification.get(
                    "preregistration_status",
                    "UNKNOWN",
                )
            ),
            "underlying_local_preregistration_complete": (
                underlying_verification.get(
                    "local_preregistration_complete",
                    False,
                )
                is True
            ),
            "preregistration_seal_exact": preregistration_sealed,
            "hash_edges_exact": bool(
                registration_hash_bound
                and evidence_hash_bound
                and receipt_hash_bound
                and projection_hash_bound
                and execution_preregistration_hash_bound
            ),
            "issuance_scope_exact": issuance_scope_bound,
            "target_schemas_exact": target_schemas_exact,
            "anti_replay_registry_bound": False,
            "atomic_nonce_consumption_verified": False,
            "post_registration_receipt_issued": False,
            "stage_order": list(STAGE_ORDER),
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "local_python_verification_execution_observed": True,
            "underlying_preregistration_remains_blocked": True,
            "cross_runtime_summary_envelope_built": True,
            "node_process_executed": False,
            "signature_verified": False,
            "raw_nonce_received": False,
            "nonce_material_embedded": False,
            "anti_replay_registry_bound": False,
            "atomic_nonce_consumption_verified": False,
            "duplicate_rejection_verified": False,
            "trusted_timestamp_verified": False,
            "witness_organization_identity_verified": False,
            "independent_execution_process_witnessed": False,
            "preregistration_document_embedded": False,
            "registration_document_embedded": False,
            "execution_evidence_document_embedded": False,
            "receipt_document_embedded": False,
            "projection_document_embedded": False,
            "execution_preregistration_document_embedded": False,
            "runtime_assets_accessed": False,
            "network_accessed": False,
            "browser_visual_review_performed": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(envelope, "envelope_hash")


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1(
    document: Any,
    preregistration_document: Any,
    registration_v7_document: Any,
    registration_v7_manifest: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
    issuance_id: Any,
    nonce_commitment_sha256: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_verification_envelope_v1(
        preregistration_document,
        registration_v7_document,
        registration_v7_manifest,
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
        issuance_id,
        nonce_commitment_sha256,
    )
    sealed = _sealed_exact(document, "envelope_hash")
    exact = sealed and strict_json_contract_equal(document, expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "envelope_seal_verified": sealed,
        "envelope_exactly_rebuilt": exact,
        "envelope_status": expected.get("status") if exact else "UNKNOWN",
        "underlying_preregistration_status": (
            expected.get("verification", {}).get(
                "underlying_preregistration_status",
                "UNKNOWN",
            )
            if exact
            else "UNKNOWN"
        ),
        "execution_semantic_state": (
            expected.get("source", {}).get(
                "execution_semantic_state",
                "UNVERIFIED",
            )
            if exact
            else "UNVERIFIED"
        ),
        "envelope_hash": expected.get("envelope_hash") if exact else None,
        "blockers": (
            []
            if exact
            else ["issuance_preregistration_verification_envelope_v1_exact"]
        ),
        "anti_replay_registry_bound": False,
        "atomic_nonce_consumption_verified": False,
        "post_registration_receipt_issued": False,
        "witness_candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }
