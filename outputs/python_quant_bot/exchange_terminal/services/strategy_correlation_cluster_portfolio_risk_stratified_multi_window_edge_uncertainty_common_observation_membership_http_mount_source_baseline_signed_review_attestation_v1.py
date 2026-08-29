"""Verify a signed source-baseline review claim without self-certifying trust.

Ed25519 proves possession of a private key corresponding to a locally bound
public key.  It does not prove real-world identity, reviewer independence, key
registration governance, nonce uniqueness, replay durability, source content
observation, review completion, route registration, or mount authority.
"""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1
    as _mount_preregistration,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_intake_v1
    as _review_intake,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-mount-source-baseline-"
    "reviewer-key-registration-v1"
)
UNSIGNED_ATTESTATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-mount-source-baseline-"
    "unsigned-review-attestation-v1"
)
SIGNED_ATTESTATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-mount-source-baseline-"
    "signed-review-attestation-v1"
)
EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-multi-window-edge-"
    "uncertainty-common-observation-membership-http-mount-source-baseline-"
    "signed-review-attestation-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-edge-uncertainty-common-observation-"
    "membership-http-mount-source-baseline-signed-review-attestation-v1-lock-1"
)
REVIEW_INTAKE_IMPLEMENTATION_SHA256 = (
    "f93c16357cebe117d73899953ec0b35d7a4e781f48e1e572d6ed326c7aab7b8d"
)
KEY_ROLE = "EXTERNAL_SOURCE_BASELINE_REVIEW_SIGNER"
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation-cluster.membership-http-mount."
    "source-baseline-review.v1"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_ENCODING = "RFC8785_JCS_UTF8_RESTRICTED_SCHEMA"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
VERIFICATION_STATE = (
    "SIGNED_SOURCE_BASELINE_REVIEW_CLAIM_VERIFIED_EXTERNAL_INDEPENDENCE_UNPROVEN"
)

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UNSIGNED_KEYS = {
    "schema_version",
    "static_fingerprint",
    "status",
    "signature_contract",
    "binding",
    "facts",
    "authority",
    "blockers",
    "unsigned_attestation_hash",
}
_SIGNED_KEYS = {
    "schema_version",
    "static_fingerprint",
    "status",
    "unsigned_binding",
    "signature",
    "facts",
    "authority",
    "blockers",
    "signed_attestation_hash",
}


class SourceBaselineSignedReviewContractError(ValueError):
    """Raised when signed-review input is malformed or unverifiable."""


def _plain_mapping(value: Any) -> bool:
    return type(value) is dict


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not _plain_mapping(value):
        raise SourceBaselineSignedReviewContractError(f"{label} must be a dict")
    return value


def _require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    result = _require_mapping(value, label)
    if set(result) != expected:
        raise SourceBaselineSignedReviewContractError(f"{label} keys do not match schema")
    return result


def _require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or _HASH_RE.fullmatch(value) is None:
        raise SourceBaselineSignedReviewContractError(f"{label} must be a lowercase SHA-256")
    return value


def _require_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or _ID_RE.fullmatch(value) is None:
        raise SourceBaselineSignedReviewContractError(f"{label} is invalid")
    return value


def _decode_base64(value: Any, label: str, *, expected_length: int) -> bytes:
    if not isinstance(value, str) or not value:
        raise SourceBaselineSignedReviewContractError(f"{label} is invalid")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SourceBaselineSignedReviewContractError(f"{label} is invalid") from exc
    if len(raw) != expected_length or base64.b64encode(raw).decode("ascii") != value:
        raise SourceBaselineSignedReviewContractError(f"{label} is invalid")
    return raw


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "source_baseline_authentication_allowed": False,
        "review_completion_allowed": False,
        "review_promotion_allowed": False,
        "mount_allowed": False,
        "route_registration_allowed": False,
        "ui_consumer_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _registration_blockers() -> list[str]:
    return [
        "REVIEWER_REAL_WORLD_IDENTITY_UNPROVEN",
        "REVIEWER_PROCESS_INDEPENDENCE_UNPROVEN",
        "REVIEWER_KEY_REGISTRATION_GOVERNANCE_UNPROVEN",
        "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
        "ROUTE_NOT_REGISTERED",
    ]


def _evidence_blockers() -> list[str]:
    return [
        "REVIEWER_REAL_WORLD_IDENTITY_UNPROVEN",
        "REVIEWER_PROCESS_INDEPENDENCE_UNPROVEN",
        "REVIEWER_KEY_REGISTRATION_GOVERNANCE_UNPROVEN",
        "REVIEW_NONCE_UNIQUENESS_UNPROVEN",
        "REVIEW_REPLAY_REGISTRY_UNPROVEN",
        "SOURCE_CONTENT_REVIEW_NOT_OBSERVED_BY_SYSTEM",
        "SOURCE_BASELINE_NOT_AUTHENTICATED",
        "EXTERNAL_INDEPENDENT_REVIEW_NOT_COMPLETED",
        "ROUTE_NOT_REGISTERED",
    ]


def build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_reviewer_key_registration_v1(
    *,
    reviewer_claim_id: Any,
    reviewer_process_id: Any,
    key_id: Any,
    public_key_base64: Any,
) -> dict[str, Any]:
    claim_id = _require_identifier(reviewer_claim_id, "reviewer_claim_id")
    process_id = _require_identifier(reviewer_process_id, "reviewer_process_id")
    normalized_key_id = _require_identifier(key_id, "key_id")
    public_key = _decode_base64(public_key_base64, "public_key_base64", expected_length=32)
    document = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "LOCAL_KEY_BINDING_EXTERNAL_GOVERNANCE_UNPROVEN",
        "reviewer_binding": {
            "reviewer_claim_id_sha256": strict_canonical_hash(
                {"reviewer_claim_id": claim_id}
            ),
            "reviewer_process_id_sha256": strict_canonical_hash(
                {"reviewer_process_id": process_id}
            ),
        },
        "key_binding": {
            "key_id": normalized_key_id,
            "key_role": KEY_ROLE,
            "algorithm": SIGNATURE_ALGORITHM,
            "public_key_sha256": _sha256_bytes(public_key),
        },
        "review_scope": {
            "request_schema_version": _review_intake.REQUEST_SCHEMA_VERSION,
            "claim_schema_version": _review_intake.CLAIM_SCHEMA_VERSION,
            "intake_schema_version": _review_intake.INTAKE_SCHEMA_VERSION,
            "source_role": "HTTP_MOUNT_SERVER_AND_CONTRACT_BASELINE",
        },
        "facts": {
            "reviewer_identifiers_embedded": False,
            "public_key_material_embedded": False,
            "real_world_reviewer_identity_verified": False,
            "reviewer_process_independence_verified": False,
            "registration_governance_verified": False,
            "independent_review_complete": False,
            "route_registered": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": _registration_blockers(),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def _validate_registration(
    registration: Any,
    review_claim: Any,
    public_key_base64: Any,
    expected_registration_hash: Any,
) -> tuple[dict[str, Any], bytes]:
    document = _require_mapping(registration, "registration")
    claim = _require_mapping(review_claim, "review_claim")
    expected_hash = _require_hash(expected_registration_hash, "expected_registration_hash")
    key_binding = _require_mapping(document.get("key_binding"), "key_binding")
    key_id = _require_identifier(key_binding.get("key_id"), "key_id")
    public_key = _decode_base64(public_key_base64, "public_key_base64", expected_length=32)
    expected = build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_reviewer_key_registration_v1(
        reviewer_claim_id=claim.get("reviewer_claim_id"),
        reviewer_process_id=claim.get("reviewer_process_id"),
        key_id=key_id,
        public_key_base64=public_key_base64,
    )
    if document.get("registration_hash") != expected_hash or not strict_json_contract_equal(
        document, expected
    ):
        raise SourceBaselineSignedReviewContractError("registration is not exact")
    return document, public_key


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_reviewer_key_registration_v1(
    document: Any,
    review_claim: Any,
    public_key_base64: Any,
    *,
    expected_registration_hash: Any,
) -> bool:
    try:
        _validate_registration(
            document, review_claim, public_key_base64, expected_registration_hash
        )
    except Exception:
        return False
    return True


def _validate_review_chain(
    review_request_document: Any,
    review_claim: Any,
    claim_intake_document: Any,
    mount_preregistration_document: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = _require_mapping(review_request_document, "review_request_document")
    claim = _require_mapping(review_claim, "review_claim")
    intake = _require_mapping(claim_intake_document, "claim_intake_document")
    preregistration = _require_mapping(
        mount_preregistration_document, "mount_preregistration_document"
    )
    if not _mount_preregistration.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_preregistration_v1(
        preregistration
    ):
        raise SourceBaselineSignedReviewContractError("mount preregistration is not exact")
    if not _review_intake.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_request_v1(
        request, preregistration
    ):
        raise SourceBaselineSignedReviewContractError("review request is not exact")
    if not _review_intake.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_claim_intake_v1(
        intake, request, claim, preregistration
    ):
        raise SourceBaselineSignedReviewContractError("claim intake is not exact")
    facts = _require_mapping(intake.get("facts"), "claim_intake facts")
    if (
        intake.get("review_state") != "CLAIM_BOUND_UNAUTHENTICATED"
        or facts.get("review_claim_bound") is not True
        or facts.get("source_baseline_authenticated") is not False
        or facts.get("independent_review_complete") is not False
    ):
        raise SourceBaselineSignedReviewContractError("claim intake is not signable")
    return request, claim, intake, preregistration


def build_unsigned_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_attestation_v1(
    registration: Any,
    review_request_document: Any,
    review_claim: Any,
    claim_intake_document: Any,
    mount_preregistration_document: Any,
    public_key_base64: Any,
    *,
    expected_registration_hash: Any,
    review_nonce_hash: Any,
) -> dict[str, Any]:
    request, claim, intake, preregistration = _validate_review_chain(
        review_request_document,
        review_claim,
        claim_intake_document,
        mount_preregistration_document,
    )
    registered, _ = _validate_registration(
        registration, claim, public_key_base64, expected_registration_hash
    )
    nonce_hash = _require_hash(review_nonce_hash, "review_nonce_hash")
    source = _require_mapping(intake.get("source"), "claim_intake source")
    document = {
        "schema_version": UNSIGNED_ATTESTATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "AWAITING_DETACHED_SIGNATURE",
        "signature_contract": {
            "domain": SIGNATURE_DOMAIN,
            "algorithm": SIGNATURE_ALGORITHM,
            "encoding": SIGNATURE_ENCODING,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "binding": {
            "registration_hash": registered["registration_hash"],
            "key_id": registered["key_binding"]["key_id"],
            "review_request_hash": request["review_request_hash"],
            "claim_intake_hash": intake["intake_hash"],
            "review_claim_sha256": source["review_claim_sha256"],
            "mount_preregistration_hash": preregistration["preregistration_hash"],
            "observed_source_hashes": copy.deepcopy(source["observed_source_hashes"]),
            "review_nonce_hash": nonce_hash,
            "review_intake_implementation_sha256": REVIEW_INTAKE_IMPLEMENTATION_SHA256,
        },
        "facts": {
            "registration_exactly_verified": True,
            "review_chain_exactly_verified": True,
            "claim_bound_unauthenticated": True,
            "signature_present": False,
            "signature_verified": False,
            "source_baseline_authenticated": False,
            "independent_review_complete": False,
            "route_registered": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": ["DETACHED_SIGNATURE_ABSENT", *_evidence_blockers()],
    }
    return seal_strict_canonical_document(document, "unsigned_attestation_hash")


def _validate_unsigned_shape(document: Any) -> dict[str, Any]:
    unsigned = _require_exact_keys(document, _UNSIGNED_KEYS, "unsigned_attestation")
    if (
        unsigned.get("schema_version") != UNSIGNED_ATTESTATION_SCHEMA_VERSION
        or unsigned.get("static_fingerprint") != STATIC_FINGERPRINT
        or unsigned.get("status") != "AWAITING_DETACHED_SIGNATURE"
        or not _require_hash(
            unsigned.get("unsigned_attestation_hash"), "unsigned_attestation_hash"
        )
    ):
        raise SourceBaselineSignedReviewContractError("unsigned attestation is invalid")
    unsealed = copy.deepcopy(unsigned)
    unsealed.pop("unsigned_attestation_hash")
    expected = seal_strict_canonical_document(unsealed, "unsigned_attestation_hash")
    if not strict_json_contract_equal(unsigned, expected):
        raise SourceBaselineSignedReviewContractError("unsigned attestation seal is invalid")
    return unsigned


def assemble_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
    unsigned_attestation: Any,
    signature_base64: Any,
) -> dict[str, Any]:
    unsigned = _validate_unsigned_shape(unsigned_attestation)
    signature = _decode_base64(signature_base64, "signature_base64", expected_length=64)
    binding = _require_mapping(unsigned.get("binding"), "unsigned binding")
    document = {
        "schema_version": SIGNED_ATTESTATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "SIGNED_ATTESTATION_ASSEMBLED_UNVERIFIED",
        "unsigned_binding": {
            "unsigned_attestation_hash": unsigned["unsigned_attestation_hash"],
            "registration_hash": binding["registration_hash"],
            "key_id": binding["key_id"],
            "review_request_hash": binding["review_request_hash"],
            "claim_intake_hash": binding["claim_intake_hash"],
            "review_nonce_hash": binding["review_nonce_hash"],
        },
        "signature": {
            "algorithm": SIGNATURE_ALGORITHM,
            "encoding": "BASE64_CANONICAL",
            "signature_base64": signature_base64,
            "signature_sha256": _sha256_bytes(signature),
        },
        "facts": {
            "unsigned_attestation_exactly_bound": True,
            "signature_material_embedded": True,
            "signature_verified": False,
            "source_baseline_authenticated": False,
            "independent_review_complete": False,
            "route_registered": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": ["DETACHED_SIGNATURE_NOT_YET_VERIFIED", *_evidence_blockers()],
    }
    return seal_strict_canonical_document(document, "signed_attestation_hash")


def _validate_signed_shape(document: Any) -> dict[str, Any]:
    signed = _require_exact_keys(document, _SIGNED_KEYS, "signed_attestation")
    if (
        signed.get("schema_version") != SIGNED_ATTESTATION_SCHEMA_VERSION
        or signed.get("static_fingerprint") != STATIC_FINGERPRINT
        or signed.get("status") != "SIGNED_ATTESTATION_ASSEMBLED_UNVERIFIED"
        or not _require_hash(signed.get("signed_attestation_hash"), "signed_attestation_hash")
    ):
        raise SourceBaselineSignedReviewContractError("signed attestation is invalid")
    return signed


def evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
    registration: Any,
    signed_attestation: Any,
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
    signed = _validate_signed_shape(signed_attestation)
    expected_signed_hash = _require_hash(
        expected_signed_attestation_hash, "expected_signed_attestation_hash"
    )
    registered, public_key = _validate_registration(
        registration, review_claim, public_key_base64, expected_registration_hash
    )
    unsigned = build_unsigned_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_attestation_v1(
        registered,
        review_request_document,
        review_claim,
        claim_intake_document,
        mount_preregistration_document,
        public_key_base64,
        expected_registration_hash=expected_registration_hash,
        review_nonce_hash=review_nonce_hash,
    )
    signature_document = _require_mapping(signed.get("signature"), "signature")
    signature_base64 = signature_document.get("signature_base64")
    expected_signed = assemble_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
        unsigned, signature_base64
    )
    if signed.get("signed_attestation_hash") != expected_signed_hash or not strict_json_contract_equal(
        signed, expected_signed
    ):
        raise SourceBaselineSignedReviewContractError("signed attestation is not exact")
    signature = _decode_base64(signature_base64, "signature_base64", expected_length=64)
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature, bytes.fromhex(unsigned["unsigned_attestation_hash"])
        )
    except (InvalidSignature, ValueError) as exc:
        raise SourceBaselineSignedReviewContractError("detached signature is invalid") from exc
    binding = _require_mapping(unsigned.get("binding"), "unsigned binding")
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": VERIFICATION_STATE,
        "verification_state": VERIFICATION_STATE,
        "source_lineage": {
            "registration_hash": registered["registration_hash"],
            "unsigned_attestation_hash": unsigned["unsigned_attestation_hash"],
            "signed_attestation_hash": signed["signed_attestation_hash"],
            "signature_sha256": signature_document["signature_sha256"],
            "review_request_hash": binding["review_request_hash"],
            "claim_intake_hash": binding["claim_intake_hash"],
            "review_claim_sha256": binding["review_claim_sha256"],
            "review_nonce_hash": binding["review_nonce_hash"],
            "observed_source_hashes": copy.deepcopy(binding["observed_source_hashes"]),
            "review_intake_implementation_sha256": REVIEW_INTAKE_IMPLEMENTATION_SHA256,
        },
        "facts": {
            "reviewer_key_registration_exactly_verified": True,
            "review_chain_exactly_verified": True,
            "signed_attestation_exactly_verified": True,
            "registered_public_key_hash_verified": True,
            "detached_signature_verified": True,
            "raw_reviewer_identifiers_embedded": False,
            "public_key_material_embedded": False,
            "signature_material_embedded": False,
            "real_world_reviewer_identity_verified": False,
            "reviewer_process_independence_verified": False,
            "registration_governance_verified": False,
            "review_nonce_uniqueness_verified": False,
            "replay_registry_verified": False,
            "source_content_review_observed_by_system": False,
            "source_baseline_authenticated": False,
            "independent_review_complete": False,
            "route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": _evidence_blockers(),
    }
    return seal_strict_canonical_document(evidence, "evidence_hash")


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_evidence_v1(
    document: Any,
    registration: Any,
    signed_attestation: Any,
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
    if not _plain_mapping(document):
        return False
    try:
        expected = evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1(
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
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "EVIDENCE_SCHEMA_VERSION",
    "KEY_ROLE",
    "REGISTRATION_SCHEMA_VERSION",
    "REVIEW_INTAKE_IMPLEMENTATION_SHA256",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_DOMAIN",
    "SIGNED_ATTESTATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "SourceBaselineSignedReviewContractError",
    "UNSIGNED_ATTESTATION_SCHEMA_VERSION",
    "VERIFICATION_STATE",
    "assemble_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1",
    "build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_reviewer_key_registration_v1",
    "build_unsigned_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_review_attestation_v1",
    "evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_reviewer_key_registration_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_edge_uncertainty_common_observation_membership_http_mount_source_baseline_signed_review_attestation_evidence_v1",
]
