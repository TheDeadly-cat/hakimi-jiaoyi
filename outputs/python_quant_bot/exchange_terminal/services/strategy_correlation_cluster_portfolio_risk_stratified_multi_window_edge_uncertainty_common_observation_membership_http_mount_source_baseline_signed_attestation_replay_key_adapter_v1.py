"""Exact ADR0274 signed-evidence to ADR0275 replay-key adapter.

The adapter is pure, unmounted, and fail-closed.  It delegates source evidence
verification to ADR0274 and target construction to ADR0275 so callers do not
manually splice commitment fields across versioned contracts.
"""

from __future__ import annotations

from typing import Any, Mapping

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_nonce_replay_snapshot_gate_v1 import (
    build_nonce_replay_key_v1,
)
from exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1 import (
    SourceBaselineSignedReviewContractError,
    verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_evidence_v1,
)


STATIC_FINGERPRINT = "20260823-signed-attestation-replay-key-adapter-1"
ADAPTER_SCHEMA = (
    "strategy-correlation-cluster-signed-attestation-replay-key-adapter-v1"
)


def _build_adapter_document(
    *,
    status: str,
    mapping_status: str,
    reason_code: str,
    source_schema_version: str | None,
    source_evidence_hash: str | None,
    source_registration_hash: str | None,
    source_signed_attestation_hash: str | None,
    replay_key: dict[str, Any] | None,
    source_evidence_exactly_verified: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": ADAPTER_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "mapping_status": mapping_status,
        "reason_code": reason_code,
        "permission_state": "UNKNOWN",
        "source_schema_version": source_schema_version,
        "source_evidence_hash": source_evidence_hash,
        "source_registration_hash": source_registration_hash,
        "source_signed_attestation_hash": source_signed_attestation_hash,
        "target_schema_version": (
            replay_key["schema_version"] if replay_key is not None else None
        ),
        "replay_key": replay_key,
        "facts": {
            "source_evidence_exactly_verified": source_evidence_exactly_verified,
            "field_mapping_count": 3 if source_evidence_exactly_verified else 0,
            "manual_field_extraction_required": False,
            "raw_reviewer_identifiers_embedded": False,
            "public_key_material_embedded": False,
            "signature_material_embedded": False,
            "replay_registry_verified": False,
            "nonce_uniqueness_verified": False,
            "durable_commit_verified": False,
            "profitability_proven": False,
        },
        "authority": {
            "descriptive_only": True,
            "writer_allowed": False,
            "route_registration_allowed": False,
            "ui_consumer_mount_allowed": False,
            "current_admission_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "adapter_receipt_hash")


def _unknown_adapter(reason_code: str) -> dict[str, Any]:
    return _build_adapter_document(
        status="UNKNOWN",
        mapping_status="UNKNOWN",
        reason_code=reason_code,
        source_schema_version=None,
        source_evidence_hash=None,
        source_registration_hash=None,
        source_signed_attestation_hash=None,
        replay_key=None,
        source_evidence_exactly_verified=False,
    )


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1(
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
    """Verify ADR0274 exactly and map its three commitments to ADR0275."""

    try:
        source_exact = verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_evidence_v1(
            signed_attestation_evidence,
            registration,
            signed_attestation,
            review_request_document,
            review_claim,
            claim_intake_document,
            mount_preregistration_document,
            public_key_base64,
            expected_registration_hash=expected_registration_hash,
            expected_signed_attestation_hash=expected_signed_attestation_hash,
            review_nonce_hash=review_nonce_hash,
        )
    except (SourceBaselineSignedReviewContractError, KeyError, TypeError, ValueError):
        source_exact = False
    if source_exact is not True:
        return _unknown_adapter("SOURCE_SIGNED_ATTESTATION_EVIDENCE_NOT_EXACT")

    try:
        signed_attestation_hash = signed_attestation_evidence["source_lineage"][
            "signed_attestation_hash"
        ]
        reviewer_key_sha256 = registration["key_binding"]["public_key_sha256"]
        mapped_review_nonce_hash = signed_attestation_evidence["source_lineage"][
            "review_nonce_hash"
        ]
        if (
            signed_attestation_hash != expected_signed_attestation_hash
            or signed_attestation_hash
            != signed_attestation["signed_attestation_hash"]
            or mapped_review_nonce_hash != review_nonce_hash
            or registration["registration_hash"] != expected_registration_hash
        ):
            return _unknown_adapter("SOURCE_COMMITMENT_RELATION_NOT_EXACT")
        replay_key = build_nonce_replay_key_v1(
            signed_attestation_hash=signed_attestation_hash,
            reviewer_key_sha256=reviewer_key_sha256,
            review_nonce_hash=mapped_review_nonce_hash,
        )
        source_schema_version = signed_attestation_evidence["schema_version"]
        source_evidence_hash = signed_attestation_evidence["evidence_hash"]
        source_registration_hash = registration["registration_hash"]
    except (KeyError, TypeError, ValueError):
        return _unknown_adapter("SOURCE_COMMITMENT_MAPPING_INVALID")

    return _build_adapter_document(
        status="PASS",
        mapping_status="ADAPTED",
        reason_code="ADR0274_EXACT_EVIDENCE_MAPPED_TO_ADR0275_REPLAY_KEY",
        source_schema_version=source_schema_version,
        source_evidence_hash=source_evidence_hash,
        source_registration_hash=source_registration_hash,
        source_signed_attestation_hash=signed_attestation_hash,
        replay_key=replay_key,
        source_evidence_exactly_verified=True,
    )


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1(
    document: Any,
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
    rebuilt = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_attestation_replay_key_adapter_v1(
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
