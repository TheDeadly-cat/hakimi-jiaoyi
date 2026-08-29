"""Cryptographically bind an ADR0201 review claim without self-certifying trust.

This module verifies an Ed25519 signature made by a locally pinned reviewer key.
It does not establish the real-world reviewer identity, registration governance,
nonce uniqueness, replay durability, descriptor observation, or independence.
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
    strategy_correlation_cluster_portfolio_risk_render_descriptor_review_intake_v1
    as review_intake,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-render-descriptor-"
    "reviewer-key-registration-v1"
)
ATTESTATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-render-descriptor-"
    "signed-review-attestation-v1"
)
EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-render-descriptor-"
    "signed-review-attestation-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-render-descriptor-signed-review-attestation-lock-1"
)
REVIEW_INTAKE_IMPLEMENTATION_SHA256 = (
    "b37d6442b7af9383a3023e1c5430af0713a8691529167d6ff1bb64413cceb8ab"
)
KEY_ROLE = "EXTERNAL_RENDER_DESCRIPTOR_REVIEW_SIGNER"
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation-cluster.portfolio-risk."
    "render-descriptor-review.v1"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_ENCODING = "RFC8785_JCS_UTF8_RESTRICTED_SCHEMA"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
VERIFICATION_STATE = (
    "SIGNED_REVIEW_CLAIM_VERIFIED_EXTERNAL_INDEPENDENCE_UNPROVEN"
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class RenderDescriptorSignedReviewContractError(ValueError):
    """Raised when signed-review evidence is malformed or unverifiable."""


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise RenderDescriptorSignedReviewContractError(f"{label} must be a dict")
    return value


def _require_exact_keys(
    value: Any, expected: set[str] | frozenset[str], label: str
) -> dict[str, Any]:
    result = _require_dict(value, label)
    if set(result) != set(expected):
        raise RenderDescriptorSignedReviewContractError(
            f"{label} keys do not match schema"
        )
    return result


def _require_hash(value: Any, label: str) -> str:
    if type(value) is not str or _HASH_RE.fullmatch(value) is None:
        raise RenderDescriptorSignedReviewContractError(
            f"{label} must be a lowercase SHA-256"
        )
    return value


def _require_identifier(value: Any, label: str) -> str:
    if type(value) is not str or _ID_RE.fullmatch(value) is None:
        raise RenderDescriptorSignedReviewContractError(f"{label} is invalid")
    return value


def _require_reviewer_label(value: Any, label: str) -> str:
    if type(value) is not str or value != value.strip() or not 1 <= len(value) <= 128:
        raise RenderDescriptorSignedReviewContractError(f"{label} is invalid")
    return value


def _decode_base64(value: Any, label: str, *, expected_length: int) -> bytes:
    if type(value) is not str or not value:
        raise RenderDescriptorSignedReviewContractError(f"{label} is invalid")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RenderDescriptorSignedReviewContractError(
            f"{label} is invalid"
        ) from exc
    if len(raw) != expected_length or base64.b64encode(raw).decode("ascii") != value:
        raise RenderDescriptorSignedReviewContractError(f"{label} is invalid")
    return raw


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "review_completion_allowed": False,
        "review_promotion_allowed": False,
        "http_route_registration_allowed": False,
        "presentation_mount_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _registration_blockers() -> list[str]:
    return [
        "reviewer_real_world_identity_unproven",
        "reviewer_process_independence_unproven",
        "reviewer_key_registration_governance_unproven",
        "external_independent_review_not_completed",
    ]


def _evidence_blockers() -> list[str]:
    return [
        "reviewer_real_world_identity_unproven",
        "reviewer_process_independence_unproven",
        "reviewer_key_registration_governance_unproven",
        "review_nonce_uniqueness_unproven",
        "review_replay_registry_unproven",
        "descriptor_content_review_not_observed_by_system",
        "external_independent_review_not_completed",
        "presentation_registration_not_activated",
    ]


def build_strategy_correlation_cluster_portfolio_risk_render_descriptor_reviewer_key_registration_v1(
    *,
    reviewer_claim_id: Any,
    reviewer_process_id: Any,
    key_id: Any,
    public_key_base64: Any,
) -> dict[str, Any]:
    """Build a redacted local key binding, not an external identity registry."""

    claim_id = _require_reviewer_label(reviewer_claim_id, "reviewer_claim_id")
    process_id = _require_reviewer_label(
        reviewer_process_id, "reviewer_process_id"
    )
    normalized_key_id = _require_identifier(key_id, "key_id")
    public_key = _decode_base64(
        public_key_base64, "public_key_base64", expected_length=32
    )
    document: dict[str, Any] = {
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
            "request_schema_version": review_intake.REQUEST_SCHEMA_VERSION,
            "claim_schema_version": review_intake.CLAIM_SCHEMA_VERSION,
            "intake_schema_version": review_intake.INTAKE_SCHEMA_VERSION,
            "descriptor_role": "PORTFOLIO_RISK_PRESENTATION_RENDER_DESCRIPTOR",
        },
        "facts": {
            "reviewer_identifiers_embedded": False,
            "public_key_material_embedded": False,
            "real_world_reviewer_identity_verified": False,
            "reviewer_process_independence_verified": False,
            "registration_governance_verified": False,
            "independent_review_complete": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": _registration_blockers(),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def _validate_registration(
    registration: Any,
    *,
    reviewer_claim_id: Any,
    reviewer_process_id: Any,
    key_id: Any,
    public_key_base64: Any,
    expected_registration_hash: Any,
) -> tuple[dict[str, Any], bytes]:
    expected_hash = _require_hash(
        expected_registration_hash, "expected_registration_hash"
    )
    expected = build_strategy_correlation_cluster_portfolio_risk_render_descriptor_reviewer_key_registration_v1(
        reviewer_claim_id=reviewer_claim_id,
        reviewer_process_id=reviewer_process_id,
        key_id=key_id,
        public_key_base64=public_key_base64,
    )
    if not strict_json_contract_equal(registration, expected):
        raise RenderDescriptorSignedReviewContractError(
            "reviewer key registration does not rebuild exactly"
        )
    if expected["registration_hash"] != expected_hash:
        raise RenderDescriptorSignedReviewContractError(
            "expected registration hash mismatch"
        )
    public_key = _decode_base64(
        public_key_base64, "public_key_base64", expected_length=32
    )
    return expected, public_key


def verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_reviewer_key_registration_v1(
    registration: Any,
    *,
    reviewer_claim_id: Any,
    reviewer_process_id: Any,
    key_id: Any,
    public_key_base64: Any,
    expected_registration_hash: Any,
) -> bool:
    try:
        _validate_registration(
            registration,
            reviewer_claim_id=reviewer_claim_id,
            reviewer_process_id=reviewer_process_id,
            key_id=key_id,
            public_key_base64=public_key_base64,
            expected_registration_hash=expected_registration_hash,
        )
    except Exception:
        return False
    return True


def _validate_review_sources(
    review_request_document: Any,
    review_claim: Any,
    claim_intake_document: Any,
    preregistration_v9_document: Any,
    *,
    v9_verification_context: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = _require_dict(review_request_document, "review_request_document")
    claim = _require_dict(review_claim, "review_claim")
    intake = _require_dict(claim_intake_document, "claim_intake_document")
    try:
        request_exact = review_intake.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_request_v1(
            request,
            preregistration_v9_document,
            v9_verification_context=v9_verification_context,
        )
        intake_exact = review_intake.verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_claim_intake_v1(
            intake,
            request,
            claim,
            preregistration_v9_document,
            v9_verification_context=v9_verification_context,
        )
    except Exception as exc:
        raise RenderDescriptorSignedReviewContractError(
            "ADR0201 source verification failed"
        ) from exc
    if not request_exact or request.get("status") != "AWAITING_EXTERNAL_INDEPENDENT_REVIEW":
        raise RenderDescriptorSignedReviewContractError(
            "review request is not exact and awaiting external review"
        )
    if (
        not intake_exact
        or intake.get("status")
        != "LOCAL_REVIEW_CLAIM_BOUND_EXTERNAL_INDEPENDENCE_UNPROVEN"
        or intake.get("review_state") != "CLAIM_BOUND_UNVERIFIED"
    ):
        raise RenderDescriptorSignedReviewContractError(
            "review claim intake is not exact and claim-bound-unverified"
        )
    facts = _require_dict(intake.get("facts"), "claim_intake_document.facts")
    if (
        facts.get("review_claim_bound") is not True
        or facts.get("attestation_signature_verified") is not False
        or facts.get("independent_review_complete") is not False
    ):
        raise RenderDescriptorSignedReviewContractError(
            "review intake authority boundary drifted"
        )
    return request, claim, intake


def build_unsigned_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_attestation_v1(
    registration: Any,
    review_request_document: Any,
    review_claim: Any,
    claim_intake_document: Any,
    preregistration_v9_document: Any,
    public_key_base64: Any,
    *,
    key_id: Any,
    expected_registration_hash: Any,
    review_nonce_hash: Any,
    v9_verification_context: Any,
) -> dict[str, Any]:
    """Build the exact digest payload an external reviewer key must sign."""

    claim_value = _require_dict(review_claim, "review_claim")
    claim_id = claim_value.get("reviewer_claim_id")
    process_id = claim_value.get("reviewer_process_id")
    registered, _ = _validate_registration(
        registration,
        reviewer_claim_id=claim_id,
        reviewer_process_id=process_id,
        key_id=key_id,
        public_key_base64=public_key_base64,
        expected_registration_hash=expected_registration_hash,
    )
    request, claim, intake = _validate_review_sources(
        review_request_document,
        review_claim,
        claim_intake_document,
        preregistration_v9_document,
        v9_verification_context=v9_verification_context,
    )
    nonce_hash = _require_hash(review_nonce_hash, "review_nonce_hash")
    source = _require_dict(intake.get("source"), "claim_intake_document.source")
    target = _require_dict(request.get("review_target"), "review_request_document.review_target")
    reviewer_binding = registered["reviewer_binding"]
    if (
        source.get("review_request_hash") != request.get("review_request_hash")
        or source.get("descriptor_sha256") != target.get("descriptor_sha256")
        or source.get("reviewer_claim_id_sha256")
        != reviewer_binding["reviewer_claim_id_sha256"]
        or source.get("reviewer_process_id_sha256")
        != reviewer_binding["reviewer_process_id_sha256"]
    ):
        raise RenderDescriptorSignedReviewContractError(
            "registration, request, and intake lineage mismatch"
        )
    document: dict[str, Any] = {
        "schema_version": ATTESTATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_hash": registered["registration_hash"],
        "review_binding": {
            "review_request_hash": request["review_request_hash"],
            "claim_intake_hash": intake["intake_hash"],
            "descriptor_sha256": target["descriptor_sha256"],
            "preregistration_v9_sha256": target["preregistration_v9_sha256"],
            "review_claim_sha256": strict_canonical_hash(claim),
            "reviewer_claim_id_sha256": reviewer_binding[
                "reviewer_claim_id_sha256"
            ],
            "reviewer_process_id_sha256": reviewer_binding[
                "reviewer_process_id_sha256"
            ],
            "review_nonce_hash": nonce_hash,
        },
        "signer": copy.deepcopy(registered["key_binding"]),
        "signature_contract": {
            "domain": SIGNATURE_DOMAIN,
            "algorithm": SIGNATURE_ALGORITHM,
            "encoding": SIGNATURE_ENCODING,
            "message_format": SIGNATURE_MESSAGE_FORMAT,
        },
        "source_contract": {
            "review_intake_static_fingerprint": review_intake.STATIC_FINGERPRINT,
            "review_intake_implementation_sha256": REVIEW_INTAKE_IMPLEMENTATION_SHA256,
        },
    }
    return seal_strict_canonical_document(document, "unsigned_attestation_hash")


_UNSIGNED_KEYS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "registration_hash",
        "review_binding",
        "signer",
        "signature_contract",
        "source_contract",
        "unsigned_attestation_hash",
    }
)


def _validate_unsigned_seal_only(value: Any) -> dict[str, Any]:
    unsigned = _require_exact_keys(value, _UNSIGNED_KEYS, "unsigned_attestation")
    if unsigned.get("schema_version") != ATTESTATION_SCHEMA_VERSION:
        raise RenderDescriptorSignedReviewContractError("attestation schema mismatch")
    if unsigned.get("static_fingerprint") != STATIC_FINGERPRINT:
        raise RenderDescriptorSignedReviewContractError(
            "attestation fingerprint mismatch"
        )
    _require_hash(unsigned.get("registration_hash"), "registration_hash")
    binding = _require_exact_keys(
        unsigned.get("review_binding"),
        {
            "review_request_hash",
            "claim_intake_hash",
            "descriptor_sha256",
            "preregistration_v9_sha256",
            "review_claim_sha256",
            "reviewer_claim_id_sha256",
            "reviewer_process_id_sha256",
            "review_nonce_hash",
        },
        "unsigned_attestation.review_binding",
    )
    for field, field_value in binding.items():
        _require_hash(field_value, field)
    signer = _require_exact_keys(
        unsigned.get("signer"),
        {"key_id", "key_role", "algorithm", "public_key_sha256"},
        "unsigned_attestation.signer",
    )
    _require_identifier(signer.get("key_id"), "signer.key_id")
    _require_hash(signer.get("public_key_sha256"), "signer.public_key_sha256")
    if signer.get("key_role") != KEY_ROLE or signer.get("algorithm") != SIGNATURE_ALGORITHM:
        raise RenderDescriptorSignedReviewContractError("signer contract mismatch")
    signature_contract = _require_exact_keys(
        unsigned.get("signature_contract"),
        {"domain", "algorithm", "encoding", "message_format"},
        "unsigned_attestation.signature_contract",
    )
    if signature_contract != {
        "domain": SIGNATURE_DOMAIN,
        "algorithm": SIGNATURE_ALGORITHM,
        "encoding": SIGNATURE_ENCODING,
        "message_format": SIGNATURE_MESSAGE_FORMAT,
    }:
        raise RenderDescriptorSignedReviewContractError(
            "signature contract mismatch"
        )
    source_contract = _require_exact_keys(
        unsigned.get("source_contract"),
        {
            "review_intake_static_fingerprint",
            "review_intake_implementation_sha256",
        },
        "unsigned_attestation.source_contract",
    )
    if source_contract != {
        "review_intake_static_fingerprint": review_intake.STATIC_FINGERPRINT,
        "review_intake_implementation_sha256": REVIEW_INTAKE_IMPLEMENTATION_SHA256,
    }:
        raise RenderDescriptorSignedReviewContractError(
            "review intake source contract mismatch"
        )
    claimed_hash = _require_hash(
        unsigned.get("unsigned_attestation_hash"), "unsigned_attestation_hash"
    )
    payload = copy.deepcopy(unsigned)
    payload.pop("unsigned_attestation_hash")
    rebuilt = seal_strict_canonical_document(payload, "unsigned_attestation_hash")
    if rebuilt.get("unsigned_attestation_hash") != claimed_hash or not strict_json_contract_equal(
        unsigned, rebuilt
    ):
        raise RenderDescriptorSignedReviewContractError(
            "unsigned attestation seal mismatch"
        )
    return unsigned


def assemble_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1(
    unsigned_attestation: Any,
    signature_base64: Any,
) -> dict[str, Any]:
    """Attach a detached signature without accepting reviewer private keys."""

    unsigned = _validate_unsigned_seal_only(unsigned_attestation)
    signature = _decode_base64(
        signature_base64, "signature_base64", expected_length=64
    )
    document = copy.deepcopy(unsigned)
    document["signature"] = {
        "signature_base64": signature_base64,
        "signature_sha256": _sha256_bytes(signature),
    }
    return seal_strict_canonical_document(document, "attestation_hash")


_SIGNED_KEYS = _UNSIGNED_KEYS | {"signature", "attestation_hash"}


def _validate_signed_seal_only(
    value: Any,
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    signed = _require_exact_keys(value, _SIGNED_KEYS, "signed_attestation")
    unsigned = {key: copy.deepcopy(signed[key]) for key in _UNSIGNED_KEYS}
    _validate_unsigned_seal_only(unsigned)
    signature = _require_exact_keys(
        signed.get("signature"),
        {"signature_base64", "signature_sha256"},
        "signed_attestation.signature",
    )
    signature_bytes = _decode_base64(
        signature.get("signature_base64"),
        "signature.signature_base64",
        expected_length=64,
    )
    if signature.get("signature_sha256") != _sha256_bytes(signature_bytes):
        raise RenderDescriptorSignedReviewContractError("signature hash mismatch")
    claimed_hash = _require_hash(signed.get("attestation_hash"), "attestation_hash")
    payload = copy.deepcopy(signed)
    payload.pop("attestation_hash")
    rebuilt = seal_strict_canonical_document(payload, "attestation_hash")
    if rebuilt.get("attestation_hash") != claimed_hash or not strict_json_contract_equal(
        signed, rebuilt
    ):
        raise RenderDescriptorSignedReviewContractError(
            "signed attestation seal mismatch"
        )
    return signed, unsigned, signature_bytes


def evaluate_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1(
    registration: Any,
    signed_attestation: Any,
    review_request_document: Any,
    review_claim: Any,
    claim_intake_document: Any,
    preregistration_v9_document: Any,
    public_key_base64: Any,
    *,
    expected_registration_hash: Any,
    expected_signed_attestation_hash: Any,
    review_nonce_hash: Any,
    v9_verification_context: Any,
) -> dict[str, Any]:
    """Verify local cryptographic facts and preserve all external trust blockers."""

    signed, unsigned, signature = _validate_signed_seal_only(signed_attestation)
    key_id = unsigned["signer"]["key_id"]
    claim = _require_dict(review_claim, "review_claim")
    registered, public_key = _validate_registration(
        registration,
        reviewer_claim_id=claim.get("reviewer_claim_id"),
        reviewer_process_id=claim.get("reviewer_process_id"),
        key_id=key_id,
        public_key_base64=public_key_base64,
        expected_registration_hash=expected_registration_hash,
    )
    expected_unsigned = build_unsigned_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_attestation_v1(
        registered,
        review_request_document,
        claim,
        claim_intake_document,
        preregistration_v9_document,
        public_key_base64,
        key_id=key_id,
        expected_registration_hash=expected_registration_hash,
        review_nonce_hash=review_nonce_hash,
        v9_verification_context=v9_verification_context,
    )
    if not strict_json_contract_equal(unsigned, expected_unsigned):
        raise RenderDescriptorSignedReviewContractError(
            "signed attestation does not match exact review sources"
        )
    expected_attestation_hash = _require_hash(
        expected_signed_attestation_hash, "expected_signed_attestation_hash"
    )
    if signed["attestation_hash"] != expected_attestation_hash:
        raise RenderDescriptorSignedReviewContractError(
            "expected signed attestation hash mismatch"
        )
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature, bytes.fromhex(unsigned["unsigned_attestation_hash"])
        )
    except InvalidSignature as exc:
        raise RenderDescriptorSignedReviewContractError(
            "review attestation signature verification failed"
        ) from exc

    binding = unsigned["review_binding"]
    document: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "verification_state": VERIFICATION_STATE,
        "source_lineage": {
            "registration_hash": registered["registration_hash"],
            "signed_attestation_hash": signed["attestation_hash"],
            "unsigned_attestation_hash": unsigned["unsigned_attestation_hash"],
            "signature_sha256": signed["signature"]["signature_sha256"],
            "review_request_hash": binding["review_request_hash"],
            "claim_intake_hash": binding["claim_intake_hash"],
            "descriptor_sha256": binding["descriptor_sha256"],
            "review_claim_sha256": binding["review_claim_sha256"],
            "review_nonce_hash": binding["review_nonce_hash"],
            "review_intake_implementation_sha256": REVIEW_INTAKE_IMPLEMENTATION_SHA256,
        },
        "facts": {
            "reviewer_key_registration_exactly_verified": True,
            "registration_hash_pin_matched": True,
            "signed_attestation_hash_pin_matched": True,
            "review_request_exactly_verified": True,
            "claim_intake_exactly_verified": True,
            "review_claim_hash_bound": True,
            "descriptor_hash_bound": True,
            "review_nonce_hash_bound": True,
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
            "descriptor_content_review_observed_by_system": False,
            "independent_review_complete": False,
            "http_route_registered": False,
            "ui_mounted": False,
            "runtime_mutations_performed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
        "blockers": _evidence_blockers(),
    }
    return seal_strict_canonical_document(document, "evidence_hash")


def verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_evidence_v1(
    document: Any,
    registration: Any,
    signed_attestation: Any,
    review_request_document: Any,
    review_claim: Any,
    claim_intake_document: Any,
    preregistration_v9_document: Any,
    public_key_base64: Any,
    *,
    expected_registration_hash: Any,
    expected_signed_attestation_hash: Any,
    review_nonce_hash: Any,
    v9_verification_context: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = evaluate_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1(
            registration,
            signed_attestation,
            review_request_document,
            review_claim,
            claim_intake_document,
            preregistration_v9_document,
            public_key_base64,
            expected_registration_hash=expected_registration_hash,
            expected_signed_attestation_hash=expected_signed_attestation_hash,
            review_nonce_hash=review_nonce_hash,
            v9_verification_context=v9_verification_context,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)


__all__ = [
    "REGISTRATION_SCHEMA_VERSION",
    "ATTESTATION_SCHEMA_VERSION",
    "EVIDENCE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "REVIEW_INTAKE_IMPLEMENTATION_SHA256",
    "KEY_ROLE",
    "SIGNATURE_DOMAIN",
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_ENCODING",
    "SIGNATURE_MESSAGE_FORMAT",
    "VERIFICATION_STATE",
    "RenderDescriptorSignedReviewContractError",
    "build_strategy_correlation_cluster_portfolio_risk_render_descriptor_reviewer_key_registration_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_reviewer_key_registration_v1",
    "build_unsigned_strategy_correlation_cluster_portfolio_risk_render_descriptor_review_attestation_v1",
    "assemble_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1",
    "evaluate_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_render_descriptor_signed_review_attestation_evidence_v1",
]
