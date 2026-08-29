"""Source-baseline namespace preregistration for anti-replay port v2."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from exchange_terminal.application.ports.anti_replay_registry_v2 import (
    AntiReplayCompareAndConsumeCommandV2,
    COMMAND_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    build_anti_replay_compare_and_consume_request_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_atomic_reserve_protocol_v1 import (
    build_nonce_atomic_reserve_request_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1 import (
    verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1,
)


STATIC_FINGERPRINT = "20260823-source-baseline-anti-replay-namespace-v1-lock-1"
PREREGISTRATION_SCHEMA_VERSION = (
    "source-baseline-nonce-anti-replay-namespace-preregistration-v1"
)
REQUEST_CANDIDATE_SCHEMA_VERSION = (
    "source-baseline-nonce-anti-replay-request-candidate-v1"
)
SOURCE_NAMESPACE = "source-baseline-signed-review-nonce-reserve-v1"
SOURCE_REGISTRY_SCOPE = "source-baseline-signed-review-attestation-v1"
TARGET_RECEIPT_SCHEMA_VERSION = (
    "source-baseline-nonce-atomic-consumption-receipt-v1"
)

ANTI_REPLAY_REGISTRY_V1_IMPLEMENTATION_SHA256 = (
    "5eed523c3665e687c6d2f202afcea5cc93bcdee3ef4ee942a7d4f76364f380a0"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
NONCE_ATOMIC_RESERVE_PROTOCOL_V1_IMPLEMENTATION_SHA256 = (
    "c2fd919fe3fadf5a9ee3b8f8701fbfa0944e29d9a5af4d517c82281830303723"
)
SIGNED_ATTESTATION_REPLAY_KEY_ADAPTER_V1_IMPLEMENTATION_SHA256 = (
    "a6612264cbb26d21b4f32f1706e0a8d5ad8f4f13582938446b0dff2eb40293db"
)


def _policy_document() -> dict[str, Any]:
    return {
        "schema_version": "source-baseline-nonce-anti-replay-policy-v1",
        "anti_replay_namespace": SOURCE_NAMESPACE,
        "registry_scope": SOURCE_REGISTRY_SCOPE,
        "duplicate_outcome": "DUPLICATE_REJECTED",
        "conflict_outcome": "CONFLICT_REJECTED",
        "successful_outcome": "CONSUMED",
        "successful_outcome_requires_authenticated_durable_receipt": True,
        "signed_synthetic_receipt_can_authorize": False,
        "provider_structural_match_can_authorize": False,
    }


def _requirements() -> list[dict[str, Any]]:
    names = (
        "EXTERNAL_REGISTRY_IDENTITY",
        "PORT_V2_PROVIDER_CONFORMANCE",
        "ATOMIC_COMPARE_AND_CONSUME",
        "LINEARIZABLE_NAMESPACE_SCOPE",
        "DURABLE_COMMIT",
        "AUTHENTICATED_CONSUMPTION_RECEIPT",
        "TRUSTED_REGISTRY_REVISION",
    )
    return [
        {
            "requirement_id": name,
            "required": True,
            "verified": False,
        }
        for name in names
    ]


def build_source_baseline_nonce_anti_replay_namespace_preregistration_v1() -> dict[str, Any]:
    policy = _policy_document()
    scope_hash = strict_canonical_hash(
        {
            "registry_scope": SOURCE_REGISTRY_SCOPE,
            "anti_replay_namespace": SOURCE_NAMESPACE,
            "target_receipt_schema_version": TARGET_RECEIPT_SCHEMA_VERSION,
        }
    )
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": "NAMESPACE_PREREGISTERED_EXTERNAL_PROVIDER_AND_DURABLE_RECEIPT_UNBOUND",
        "namespace_contract": {
            "anti_replay_namespace": SOURCE_NAMESPACE,
            "registry_scope": SOURCE_REGISTRY_SCOPE,
            "anti_replay_scope_hash": scope_hash,
            "port_command_schema_version": COMMAND_SCHEMA_VERSION,
            "port_request_schema_version": REQUEST_SCHEMA_VERSION,
            "target_receipt_schema_version": TARGET_RECEIPT_SCHEMA_VERSION,
        },
        "policy": policy,
        "policy_hash": strict_canonical_hash(policy),
        "required_provider_evidence": _requirements(),
        "implementation_bindings": {
            "anti_replay_registry_v1_sha256": ANTI_REPLAY_REGISTRY_V1_IMPLEMENTATION_SHA256,
            "strict_canonical_sha256": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
            "nonce_atomic_reserve_protocol_v1_sha256": NONCE_ATOMIC_RESERVE_PROTOCOL_V1_IMPLEMENTATION_SHA256,
            "signed_attestation_replay_key_adapter_v1_sha256": SIGNED_ATTESTATION_REPLAY_KEY_ADAPTER_V1_IMPLEMENTATION_SHA256,
        },
        "facts": {
            "v1_namespace_compatible": False,
            "v1_modified": False,
            "port_v2_namespace_parameterized": True,
            "external_provider_bound": False,
            "external_provider_conformance_verified": False,
            "registry_identity_verified": False,
            "atomic_compare_and_consume_verified": False,
            "linearizability_verified": False,
            "durable_commit_verified": False,
            "authenticated_consumption_receipt_issued": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "provider_call_allowed": False,
            "writer_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "namespace_preregistration_hash")


def verify_source_baseline_nonce_anti_replay_namespace_preregistration_v1(
    document: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    return strict_json_contract_equal(
        dict(document),
        build_source_baseline_nonce_anti_replay_namespace_preregistration_v1(),
    )


def _build_candidate_envelope(
    *,
    status: str,
    candidate_status: str,
    reason_code: str,
    namespace_preregistration_hash: str | None,
    source_adapter_receipt_hash: str | None,
    source_reserve_request_hash: str | None,
    request_document: dict[str, Any] | None,
    command_projection: dict[str, Any] | None,
    source_chain_exactly_verified: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": REQUEST_CANDIDATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "candidate_status": candidate_status,
        "permission_state": "BLOCKED",
        "reason_code": reason_code,
        "namespace_preregistration_hash": namespace_preregistration_hash,
        "source_adapter_receipt_hash": source_adapter_receipt_hash,
        "source_reserve_request_hash": source_reserve_request_hash,
        "request_document": request_document,
        "command_projection": command_projection,
        "facts": {
            "source_chain_exactly_verified": source_chain_exactly_verified,
            "port_v2_request_exactly_built": source_chain_exactly_verified,
            "port_v2_command_constructed": source_chain_exactly_verified,
            "provider_called": False,
            "external_provider_conformance_verified": False,
            "registry_identity_verified": False,
            "atomic_compare_and_consume_verified": False,
            "linearizability_verified": False,
            "durable_commit_verified": False,
            "authenticated_consumption_receipt_issued": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "provider_call_allowed": False,
            "writer_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "request_candidate_hash")


def _unknown_candidate(reason_code: str) -> dict[str, Any]:
    return _build_candidate_envelope(
        status="UNKNOWN",
        candidate_status="UNKNOWN",
        reason_code=reason_code,
        namespace_preregistration_hash=None,
        source_adapter_receipt_hash=None,
        source_reserve_request_hash=None,
        request_document=None,
        command_projection=None,
        source_chain_exactly_verified=False,
    )


def build_source_baseline_nonce_anti_replay_request_candidate_v1(
    namespace_preregistration_document: Any,
    adapter_document: Any,
    reserve_request_document: Any,
    registration: Any,
    signed_attestation: Any,
    signed_attestation_evidence: Any,
    review_request_document: Any,
    review_claim: Any,
    claim_intake_document: Any,
    mount_preregistration_document: Any,
    public_key_base64: Any,
    *,
    expected_registration_hash: Any,
    expected_signed_attestation_hash: Any,
    review_nonce_hash: Any,
) -> dict[str, Any]:
    if not verify_source_baseline_nonce_anti_replay_namespace_preregistration_v1(
        namespace_preregistration_document
    ):
        return _unknown_candidate("NAMESPACE_PREREGISTRATION_NOT_EXACT")
    if not verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1(
        adapter_document,
        registration,
        signed_attestation,
        signed_attestation_evidence,
        review_request_document,
        review_claim,
        claim_intake_document,
        mount_preregistration_document,
        public_key_base64,
        expected_registration_hash=expected_registration_hash,
        expected_signed_attestation_hash=expected_signed_attestation_hash,
        review_nonce_hash=review_nonce_hash,
    ):
        return _unknown_candidate("SOURCE_ADAPTER_NOT_EXACT")
    try:
        replay_key = adapter_document["replay_key"]
        rebuilt_reserve_request = build_nonce_atomic_reserve_request_v1(
            candidate_replay_key=replay_key,
            expected_registry_head_hash=reserve_request_document[
                "expected_registry_head_hash"
            ],
            request_nonce_hash=reserve_request_document["request_nonce_hash"],
        )
    except (KeyError, TypeError, ValueError):
        return _unknown_candidate("SOURCE_RESERVE_REQUEST_INVALID")
    if not strict_json_contract_equal(
        reserve_request_document, rebuilt_reserve_request
    ):
        return _unknown_candidate("SOURCE_RESERVE_REQUEST_NOT_EXACT")

    namespace_contract = namespace_preregistration_document["namespace_contract"]
    request_document = build_anti_replay_compare_and_consume_request_v2(
        anti_replay_namespace=namespace_contract["anti_replay_namespace"],
        namespace_preregistration_hash=namespace_preregistration_document[
            "namespace_preregistration_hash"
        ],
        anti_replay_scope_hash=namespace_contract["anti_replay_scope_hash"],
        subject_hash=replay_key["replay_key_hash"],
        challenge_hash=replay_key["review_nonce_hash"],
        policy_hash=namespace_preregistration_document["policy_hash"],
        request_context_hash=reserve_request_document["reserve_request_hash"],
        actor_id_hash=replay_key["reviewer_key_sha256"],
        evidence_hash=adapter_document["adapter_receipt_hash"],
        target_receipt_schema_version=namespace_contract[
            "target_receipt_schema_version"
        ],
    )
    command = AntiReplayCompareAndConsumeCommandV2.from_request_document(
        request_document
    )
    return _build_candidate_envelope(
        status="BLOCKED",
        candidate_status="BUILT_PROVIDER_UNBOUND",
        reason_code="PORT_V2_REQUEST_BUILT_EXTERNAL_PROVIDER_AND_DURABLE_RECEIPT_UNBOUND",
        namespace_preregistration_hash=namespace_preregistration_document[
            "namespace_preregistration_hash"
        ],
        source_adapter_receipt_hash=adapter_document["adapter_receipt_hash"],
        source_reserve_request_hash=reserve_request_document[
            "reserve_request_hash"
        ],
        request_document=request_document,
        command_projection=asdict(command),
        source_chain_exactly_verified=True,
    )


def verify_source_baseline_nonce_anti_replay_request_candidate_v1(
    document: Any,
    namespace_preregistration_document: Any,
    adapter_document: Any,
    reserve_request_document: Any,
    registration: Any,
    signed_attestation: Any,
    signed_attestation_evidence: Any,
    review_request_document: Any,
    review_claim: Any,
    claim_intake_document: Any,
    mount_preregistration_document: Any,
    public_key_base64: Any,
    *,
    expected_registration_hash: Any,
    expected_signed_attestation_hash: Any,
    review_nonce_hash: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    rebuilt = build_source_baseline_nonce_anti_replay_request_candidate_v1(
        namespace_preregistration_document,
        adapter_document,
        reserve_request_document,
        registration,
        signed_attestation,
        signed_attestation_evidence,
        review_request_document,
        review_claim,
        claim_intake_document,
        mount_preregistration_document,
        public_key_base64,
        expected_registration_hash=expected_registration_hash,
        expected_signed_attestation_hash=expected_signed_attestation_hash,
        review_nonce_hash=review_nonce_hash,
    )
    return strict_json_contract_equal(dict(document), rebuilt)
