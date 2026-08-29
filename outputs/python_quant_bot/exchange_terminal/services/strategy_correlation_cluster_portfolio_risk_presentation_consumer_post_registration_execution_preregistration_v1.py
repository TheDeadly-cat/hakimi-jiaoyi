from __future__ import annotations

import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v4
    as evidence_v4,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7
    as registration_v7,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-risk-downside-tail-post-registration-execution-"
    "issuance-preregistration-v1"
)
STATIC_FINGERPRINT = (
    "20260823-registration-v7-receipt-v5-single-use-preregistration-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATUS = "BLOCKED"
REGISTRATION_V7_IMPLEMENTATION_SHA256 = (
    "23f1cf3fe1e8be3b3740d0b4d592a78f32f518b399e680d3cd79044a138956e2"
)
EVIDENCE_V4_IMPLEMENTATION_SHA256 = (
    "c1e9bb3f122dd94cb6fd45a9eb1f1c40ecefc539a2af9d12be5f680c5a3819b5"
)
STRICT_CANONICAL_PYTHON_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
TARGET_RECEIPT_SCHEMA_VERSION = (
    "portfolio-risk-downside-tail-consumer-post-registration-"
    "execution-receipt-v5"
)
TARGET_RECEIPT_STATIC_FINGERPRINT = (
    "20260823-downside-tail-consumer-v6-post-registration-receipt-v5-lock-1"
)
TARGET_WITNESS_POLICY_SCHEMA_VERSION = (
    "portfolio-risk-post-registration-execution-witness-policy-v2"
)
TARGET_CHALLENGE_SCHEMA_VERSION = (
    "portfolio-risk-post-registration-document-bundle-challenge-v2"
)
TARGET_ATTESTATION_SCHEMA_VERSION = (
    "portfolio-risk-post-registration-detached-attestation-v2"
)
TARGET_WITNESS_VERIFICATION_SCHEMA_VERSION = (
    "portfolio-risk-post-registration-witness-verification-candidate-v2"
)
TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION = (
    "portfolio-risk-post-registration-anti-replay-consumption-receipt-v1"
)
ANTI_REPLAY_SCOPE_SCHEMA_VERSION = (
    "portfolio-risk-post-registration-anti-replay-scope-v1"
)
ANTI_REPLAY_NAMESPACE = (
    "portfolio-risk-downside-tail-post-registration-execution-receipt-v5"
)
_ISSUANCE_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._:-]{7,127}")
_ALLOWED_SEMANTIC_STATES = {"CLEAR", "TAIL_BLOCK", "EXACT_UNKNOWN"}
_AUTHORITY = {
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


def _is_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_nonce_commitment(value: Any) -> bool:
    return bool(
        _is_hash(value)
        and value not in {"0" * 64, "f" * 64}
        and len(set(value)) >= 8
    )


def _is_issuance_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ISSUANCE_ID_PATTERN.fullmatch(value))


def _sealed_exact(document: Any, hash_field: str) -> bool:
    if not isinstance(document, dict) or not _is_hash(document.get(hash_field)):
        return False
    try:
        expected = seal_strict_canonical_document(document, hash_field)
    except (TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def _registration_verification(
    registration_v7_document: Any,
    registration_v7_manifest: Any,
    execution_evidence_v4_document: Any,
    receipt_v4_document: Any,
    receipt_v4_verification_document: Any,
    projection_v6_document: Any,
    execution_preregistration_v1_document: Any,
) -> dict[str, Any]:
    try:
        return registration_v7.verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v7(
            registration_v7_document,
            registration_v7_manifest,
            execution_evidence_v4_document,
            receipt_v4_document,
            receipt_v4_verification_document,
            projection_v6_document,
            execution_preregistration_v1_document,
        )
    except (TypeError, ValueError):
        return {"status": "BLOCK", "execution_semantic_state": "UNVERIFIED"}


def _anti_replay_scope(
    registration_hash: str,
    evidence_hash: str,
    pre_registration_receipt_hash: str,
    issuance_id: str,
    nonce_commitment_sha256: str,
) -> dict[str, Any]:
    scope = {
        "schema_version": ANTI_REPLAY_SCOPE_SCHEMA_VERSION,
        "namespace": ANTI_REPLAY_NAMESPACE,
        "registration_hash": registration_hash,
        "execution_evidence_hash": evidence_hash,
        "pre_registration_receipt_hash": pre_registration_receipt_hash,
        "issuance_id": issuance_id,
        "nonce_commitment_sha256": nonce_commitment_sha256,
        "issuance_sequence": 1,
    }
    return {
        **scope,
        "scope_hash": strict_canonical_hash(scope),
    }


def build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
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
    registration_verification = _registration_verification(
        registration_v7_document,
        registration_v7_manifest,
        execution_evidence_v4_document,
        receipt_v4_document,
        receipt_v4_verification_document,
        projection_v6_document,
        execution_preregistration_v1_document,
    )
    semantic_state = registration_verification.get(
        "execution_semantic_state",
        "UNVERIFIED",
    )
    registration_exact = bool(
        isinstance(registration_v7_document, dict)
        and registration_verification.get("status") == "PASS"
        and registration_v7_document.get("schema_version")
        == registration_v7.SCHEMA_VERSION
        and registration_v7_document.get("static_fingerprint")
        == registration_v7.STATIC_FINGERPRINT
        and registration_v7_document.get("status") == "BLOCKED"
        and _is_hash(registration_v7_document.get("registration_hash"))
        and semantic_state in _ALLOWED_SEMANTIC_STATES
    )
    issuance_id_exact = _is_issuance_id(issuance_id)
    nonce_commitment_exact = _is_nonce_commitment(nonce_commitment_sha256)

    registration_consumer = (
        registration_v7_document.get("consumer", {})
        if registration_exact
        else {}
    )
    evidence_hash = registration_consumer.get("execution_evidence_hash")
    pre_registration_receipt_hash = registration_consumer.get(
        "receipt_v4_hash"
    )
    projection_hash = registration_consumer.get("projection_v6_hash")
    execution_preregistration_hash = registration_consumer.get(
        "execution_preregistration_v1_hash"
    )
    evidence_hash_bound = bool(
        registration_exact
        and isinstance(execution_evidence_v4_document, dict)
        and _is_hash(evidence_hash)
        and evidence_hash == execution_evidence_v4_document.get("evidence_hash")
    )
    pre_registration_receipt_hash_bound = bool(
        registration_exact
        and isinstance(receipt_v4_document, dict)
        and _is_hash(pre_registration_receipt_hash)
        and pre_registration_receipt_hash
        == receipt_v4_document.get("receipt_hash")
    )
    projection_hash_bound = bool(
        registration_exact
        and isinstance(projection_v6_document, dict)
        and _is_hash(projection_hash)
        and projection_hash == projection_v6_document.get("projection_hash")
    )
    execution_preregistration_hash_bound = bool(
        registration_exact
        and isinstance(execution_preregistration_v1_document, dict)
        and _is_hash(execution_preregistration_hash)
        and execution_preregistration_hash
        == execution_preregistration_v1_document.get("preregistration_hash")
    )
    pre_registration_receipt_absence_preserved = bool(
        registration_exact
        and registration_v7_document.get("facts", {}).get(
            "pre_registration_receipt_formal_registration_bound"
        )
        is False
        and registration_v7_document.get("facts", {}).get(
            "post_registration_execution_receipt_issued"
        )
        is False
        and "POST_REGISTRATION_EXECUTION_RECEIPT_NOT_ISSUED"
        in registration_v7_document.get("blockers", [])
    )
    scope_ready = bool(
        registration_exact
        and evidence_hash_bound
        and pre_registration_receipt_hash_bound
        and projection_hash_bound
        and execution_preregistration_hash_bound
        and pre_registration_receipt_absence_preserved
        and issuance_id_exact
        and nonce_commitment_exact
    )
    scope = (
        _anti_replay_scope(
            registration_v7_document["registration_hash"],
            evidence_hash,
            pre_registration_receipt_hash,
            issuance_id,
            nonce_commitment_sha256,
        )
        if scope_ready
        else None
    )

    checks = [
        {
            "name": "registration_v7_exact_blocked_candidate",
            "ok": registration_exact,
            "blocking": True,
        },
        {
            "name": "execution_evidence_v4_hash_edge_exact",
            "ok": evidence_hash_bound,
            "blocking": True,
        },
        {
            "name": "pre_registration_receipt_v4_hash_edge_exact",
            "ok": pre_registration_receipt_hash_bound,
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
            "name": "pre_registration_receipt_absence_preserved",
            "ok": pre_registration_receipt_absence_preserved,
            "blocking": True,
        },
        {
            "name": "issuance_id_format_exact",
            "ok": issuance_id_exact,
            "blocking": True,
        },
        {
            "name": "nonce_commitment_shape_exact",
            "ok": nonce_commitment_exact,
            "blocking": True,
        },
        {
            "name": "anti_replay_scope_derivation_exact",
            "ok": scope_ready and isinstance(scope, dict),
            "blocking": True,
        },
        {
            "name": "future_receipt_witness_and_consumption_schemas_frozen",
            "ok": True,
            "blocking": True,
        },
    ]
    local_blockers = [
        check["name"] for check in checks if check.get("ok") is not True
    ]
    local_preregistration_complete = not local_blockers
    blockers = [
        "WITNESS_POLICY_V2_IMPLEMENTATION_MISSING",
        "EXTERNAL_ANTI_REPLAY_REGISTRY_UNBOUND",
        "ATOMIC_NONCE_CONSUMPTION_UNVERIFIED",
        "NONCE_ENTROPY_AND_TRUSTED_TIME_UNVERIFIED",
        "WITNESS_ORGANIZATION_IDENTITY_UNVERIFIED",
        "INDEPENDENT_EXECUTION_PROCESS_WITNESS_UNVERIFIED",
        "POST_REGISTRATION_EXECUTION_RECEIPT_V5_NOT_ISSUED",
        "BROWSER_ROUTE_MOUNT_CURRENT_AND_ACTIVATION_UNAUTHORIZED",
    ]
    if local_blockers:
        blockers = [
            f"LOCAL_PREREGISTRATION_CHECK_FAILED:{name}"
            for name in local_blockers
        ] + blockers

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": STATUS,
        "decision": (
            "POST_REGISTRATION_RECEIPT_V5_ISSUANCE_PREREGISTERED_"
            "ANTI_REPLAY_REGISTRY_WITNESS_AND_RECEIPT_UNBOUND"
            if local_preregistration_complete
            else "POST_REGISTRATION_RECEIPT_V5_ISSUANCE_PREREGISTRATION_BLOCKED"
        ),
        "source": {
            "registration_v7_schema_version": (
                registration_v7.SCHEMA_VERSION
                if registration_exact
                else "UNKNOWN"
            ),
            "registration_v7_static_fingerprint": (
                registration_v7.STATIC_FINGERPRINT
                if registration_exact
                else "UNKNOWN"
            ),
            "registration_v7_hash": (
                registration_v7_document.get("registration_hash")
                if registration_exact
                else None
            ),
            "registration_v7_implementation_sha256": (
                REGISTRATION_V7_IMPLEMENTATION_SHA256
            ),
            "execution_evidence_v4_schema_version": (
                evidence_v4.SCHEMA_VERSION if evidence_hash_bound else "UNKNOWN"
            ),
            "execution_evidence_v4_hash": (
                evidence_hash if evidence_hash_bound else None
            ),
            "execution_evidence_v4_implementation_sha256": (
                EVIDENCE_V4_IMPLEMENTATION_SHA256
            ),
            "pre_registration_receipt_v4_hash": (
                pre_registration_receipt_hash
                if pre_registration_receipt_hash_bound
                else None
            ),
            "projection_v6_hash": (
                projection_hash if projection_hash_bound else None
            ),
            "execution_preregistration_v1_hash": (
                execution_preregistration_hash
                if execution_preregistration_hash_bound
                else None
            ),
            "strict_canonical_python_sha256": (
                STRICT_CANONICAL_PYTHON_SHA256
            ),
            "execution_semantic_state": (
                semantic_state if registration_exact else "UNVERIFIED"
            ),
            "registration_document_embedded": False,
            "execution_evidence_document_embedded": False,
            "receipt_document_embedded": False,
            "projection_document_embedded": False,
            "execution_preregistration_document_embedded": False,
        },
        "issuance": {
            "issuance_id": issuance_id if issuance_id_exact else "UNKNOWN",
            "issuance_sequence": 1,
            "target_receipt_schema_version": TARGET_RECEIPT_SCHEMA_VERSION,
            "target_receipt_static_fingerprint": (
                TARGET_RECEIPT_STATIC_FINGERPRINT
            ),
            "target_witness_policy_schema_version": (
                TARGET_WITNESS_POLICY_SCHEMA_VERSION
            ),
            "target_challenge_schema_version": (
                TARGET_CHALLENGE_SCHEMA_VERSION
            ),
            "target_attestation_schema_version": (
                TARGET_ATTESTATION_SCHEMA_VERSION
            ),
            "target_witness_verification_schema_version": (
                TARGET_WITNESS_VERIFICATION_SCHEMA_VERSION
            ),
            "target_anti_replay_consumption_schema_version": (
                TARGET_ANTI_REPLAY_CONSUMPTION_SCHEMA_VERSION
            ),
            "registration_hash": (
                registration_v7_document.get("registration_hash")
                if registration_exact
                else None
            ),
            "execution_evidence_hash": (
                evidence_hash if evidence_hash_bound else None
            ),
            "pre_registration_receipt_hash": (
                pre_registration_receipt_hash
                if pre_registration_receipt_hash_bound
                else None
            ),
            "post_registration_receipt_hash": None,
        },
        "anti_replay": {
            "scope_schema_version": ANTI_REPLAY_SCOPE_SCHEMA_VERSION,
            "namespace": ANTI_REPLAY_NAMESPACE,
            "scope_hash": scope.get("scope_hash") if scope else None,
            "nonce_commitment_sha256": (
                nonce_commitment_sha256 if nonce_commitment_exact else None
            ),
            "replay_key_fields": [
                "namespace",
                "registration_hash",
                "issuance_id",
                "nonce_commitment_sha256",
            ],
            "registry_consistency_required": "LINEARIZABLE",
            "required_registry_operation": (
                "ATOMIC_PUT_IF_ABSENT_THEN_CONSUME_ONCE"
            ),
            "challenge_use_limit": 1,
            "receipt_issue_limit": 1,
            "nonce_material_embedded": False,
            "external_registry_snapshot_hash": None,
            "nonce_consumption_receipt_hash": None,
            "registry_bound": False,
            "atomic_consumption_verified": False,
            "duplicate_rejection_verified": False,
            "trusted_time_source_bound": False,
        },
        "checks": checks,
        "closed_local_blockers": (
            [
                "REGISTRATION_V7_EXACT_BLOCKED_CANDIDATE_BOUND",
                "PRE_REGISTRATION_EXECUTION_CHAIN_HASHES_BOUND",
                "POST_REGISTRATION_RECEIPT_V5_TARGET_SCHEMA_FROZEN",
                "ANTI_REPLAY_NAMESPACE_AND_SINGLE_USE_POLICY_FROZEN",
                "NONCE_COMMITMENT_BOUND_WITHOUT_NONCE_DISCLOSURE",
            ]
            if local_preregistration_complete
            else []
        ),
        "blockers": blockers,
        "activation_order": [
            "REGISTRATION_V7_STATIC_BLOCKED_CANDIDATE",
            "POST_REGISTRATION_ISSUANCE_PREREGISTRATION_V1",
            "WITNESS_POLICY_AND_CHALLENGE_V2",
            "EXTERNAL_LINEARIZABLE_ANTI_REPLAY_REGISTRY",
            "ATOMIC_NONCE_CONSUMPTION_RECEIPT_V1",
            "INDEPENDENT_WITNESS_ATTESTATION_V2",
            "POST_REGISTRATION_EXECUTION_RECEIPT_V5",
            "PYTHON_POST_REGISTRATION_RECEIPT_EVIDENCE",
            "EXPLICIT_BROWSER_VISUAL_REVIEW",
            "SEPARATE_PRODUCTION_ROUTE_OR_MOUNT_DECISION",
        ],
        "facts": {
            "issuance_preregistration_built": True,
            "local_preregistration_complete": local_preregistration_complete,
            "registration_v7_bound": registration_exact,
            "pre_registration_receipt_preserved": (
                pre_registration_receipt_absence_preserved
            ),
            "post_registration_receipt_issued": False,
            "witness_policy_v2_implemented": False,
            "raw_nonce_received": False,
            "nonce_entropy_verified": False,
            "nonce_material_embedded": False,
            "external_anti_replay_registry_bound": False,
            "atomic_nonce_consumption_verified": False,
            "duplicate_rejection_verified": False,
            "trusted_timestamp_verified": False,
            "witness_organization_identity_verified": False,
            "independent_execution_process_witnessed": False,
            "browser_visual_review_performed": False,
            "runtime_assets_accessed": False,
            "network_accessed": False,
            "runtime_consumer_bound": False,
            "ui_mounted": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def verify_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
    document: Any,
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
    expected = build_strategy_correlation_cluster_portfolio_risk_presentation_consumer_post_registration_execution_preregistration_v1(
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
    exact = isinstance(document, dict) and strict_json_contract_equal(
        document,
        expected,
    )
    seal_exact = exact and _sealed_exact(document, "preregistration_hash")
    local_complete = bool(
        expected.get("facts", {}).get("local_preregistration_complete") is True
    )
    passed = bool(exact and seal_exact and local_complete)
    blockers = []
    if not exact or not seal_exact:
        blockers.append("post_registration_preregistration_v1_exact_rebuild")
    if not local_complete:
        blockers.append("post_registration_preregistration_v1_local_complete")
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "preregistration_exactly_rebuilt": exact,
        "preregistration_seal_verified": seal_exact,
        "local_preregistration_complete": local_complete,
        "preregistration_status": (
            expected.get("status") if exact else "UNKNOWN"
        ),
        "execution_semantic_state": (
            expected.get("source", {}).get(
                "execution_semantic_state",
                "UNVERIFIED",
            )
            if exact
            else "UNVERIFIED"
        ),
        "scope_hash": (
            expected.get("anti_replay", {}).get("scope_hash")
            if passed
            else None
        ),
        "preregistration_hash": (
            expected.get("preregistration_hash") if passed else None
        ),
        "blockers": blockers,
        "anti_replay_registry_bound": False,
        "atomic_nonce_consumption_verified": False,
        "post_registration_receipt_issued": False,
        "witness_organization_identity_verified": False,
        "independent_execution_process_witnessed": False,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "post_registration_receipt_issuance_allowed": False,
        "presentation_mount_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }
