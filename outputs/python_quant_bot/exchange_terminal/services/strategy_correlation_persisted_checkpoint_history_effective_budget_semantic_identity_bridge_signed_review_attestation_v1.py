from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from typing import Any, Mapping

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - exercised only in dependency-failure environments.
    InvalidSignature = ValueError  # type: ignore[assignment]
    Ed25519PublicKey = None  # type: ignore[assignment,misc]

from exchange_terminal.services import (
    strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1
    as source_binding,
)


REVIEWER_KEY_REGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-semantic-identity-bridge-reviewer-key-registration-v1"
)
BRIDGE_CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-persisted-history-effective-budget-semantic-identity-bridge-claim-v1"
)
UNSIGNED_ATTESTATION_SCHEMA_VERSION = (
    "strategy-correlation-persisted-history-effective-budget-semantic-identity-bridge-unsigned-attestation-v1"
)
SIGNED_ATTESTATION_SCHEMA_VERSION = (
    "strategy-correlation-persisted-history-effective-budget-semantic-identity-bridge-signed-attestation-v1"
)
EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-persisted-history-effective-budget-semantic-identity-bridge-signed-review-evidence-v1"
)
SOURCE_PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-persisted-checkpoint-history-coverage-effective-budget-provenance-binding-preregistration-v1"
)
SOURCE_STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-checkpoint-history-coverage-effective-budget-"
    "provenance-binding-v1-synthetic-unmounted-dual-pin-lock-1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-persisted-history-effective-budget-semantic-identity-"
    "bridge-signed-review-attestation-v1-synthetic-unmounted-authority-lock-1"
)
SOURCE_IDENTITY_RELATIONSHIP_POLICY = (
    "EXACT_DUAL_SOURCE_PIN_NO_SEMANTIC_IDENTITY_EQUIVALENCE_CLAIM"
)
RELATIONSHIP_CLAIM = (
    "SAME_RESEARCH_INTENT_DISTINCT_TECHNICAL_WINDOW_IDENTITIES_REVIEW_CLAIM"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = "STRICT_CANONICAL_SHA256_DIGEST_V1"
SIGNATURE_DOMAIN = (
    "hakimi-v2/strategy-correlation/semantic-identity-bridge/signed-review-attestation/v1"
)
POSITIVE_STATE = (
    "SIGNED_SEMANTIC_IDENTITY_BRIDGE_CLAIM_VERIFIED_"
    "EXTERNAL_REVIEW_GOVERNANCE_UNPROVEN"
)
UNKNOWN_STATE = "UNKNOWN"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_ASCII_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,127}$")
_SOURCE_CONTEXT_KEYS = {
    "history_coverage_registration",
    "history_coverage_registration_receipt",
    "uncertainty_budget_binding_preregistration",
    "budget_binding_preregistration_verification_context",
}
_SOURCE_HASH_FIELDS = (
    "binding_contract_hash",
    "budget_binding_contract_hash",
    "budget_binding_preregistration_hash",
    "budget_cluster_partition_hash",
    "budget_symbol_order_hash",
    "budget_window_order_hash",
    "history_coverage_gate_contract_hash",
    "history_coverage_registration_receipt_hash",
    "history_study_identity_hash",
    "history_window_order_hash",
    "preregistration_hash",
)


def _authority_lock() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "effective_budget_activation_allowed": False,
        "http_registration_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "review_promotion_allowed": False,
        "runtime_activation_allowed": False,
        "semantic_identity_equivalence_claim_allowed": False,
        "writer_allowed": False,
        "research_evidence_only": True,
    }


def _canonical_bytes(value: Any) -> bytes | None:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None


def _digest(value: Any) -> str | None:
    encoded = _canonical_bytes(value)
    if encoded is None:
        return None
    return hashlib.sha256(encoded).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _seal(core: Mapping[str, Any], hash_field: str) -> dict[str, Any] | None:
    payload = dict(core)
    digest = _digest(payload)
    if digest is None:
        return None
    payload[hash_field] = digest
    return payload


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _is_ascii_id(value: Any) -> bool:
    return isinstance(value, str) and _ASCII_ID_RE.fullmatch(value) is not None


def _is_text(value: Any, *, minimum: int = 1, maximum: int = 4096) -> bool:
    return isinstance(value, str) and minimum <= len(value) <= maximum


def _decode_base64(value: Any, expected_length: int) -> bytes | None:
    if not isinstance(value, str):
        return None
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(decoded) != expected_length:
        return None
    if base64.b64encode(decoded).decode("ascii") != value:
        return None
    return decoded


def _has_exact_keys(document: Any, expected: set[str]) -> bool:
    return isinstance(document, Mapping) and set(document.keys()) == expected


def _sealed_exactly(
    document: Any,
    *,
    expected_keys: set[str],
    hash_field: str,
    expected_hash: Any,
) -> bool:
    if not _has_exact_keys(document, expected_keys):
        return False
    if not _is_hash(expected_hash) or document.get(hash_field) != expected_hash:
        return False
    core = {key: value for key, value in document.items() if key != hash_field}
    return _digest(core) == expected_hash


def _source_authority_is_locked(document: Mapping[str, Any]) -> bool:
    authority = document.get("authority")
    if not isinstance(authority, Mapping):
        return False
    required_false = (
        "current_admission_allowed",
        "current_pointer_written",
        "effective_budget_activation_allowed",
        "http_registration_allowed",
        "live_order_allowed",
        "paper_authorized",
        "profitability_claim_allowed",
        "runtime_activation_allowed",
        "semantic_identity_equivalence_claim_allowed",
        "writer_allowed",
    )
    return authority.get("research_evidence_only") is True and all(
        authority.get(field) is False for field in required_false
    )


def _verify_source_preregistration(
    document: Any,
    *,
    expected_preregistration_hash: Any,
    verification_context: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    if not _is_hash(expected_preregistration_hash):
        return False
    if not isinstance(verification_context, Mapping):
        return False
    if set(verification_context.keys()) != _SOURCE_CONTEXT_KEYS:
        return False
    if document.get("schema_version") != SOURCE_PREREGISTRATION_SCHEMA_VERSION:
        return False
    if document.get("static_fingerprint") != SOURCE_STATIC_FINGERPRINT:
        return False
    if document.get("status") != "PREREGISTERED":
        return False
    if document.get("identity_relationship_policy") != SOURCE_IDENTITY_RELATIONSHIP_POLICY:
        return False
    if document.get("preregistration_hash") != expected_preregistration_hash:
        return False
    if any(not _is_hash(document.get(field)) for field in _SOURCE_HASH_FIELDS):
        return False
    if document.get("source_window_order_hashes_equal") is not False:
        return False
    if document.get("history_window_order_hash") == document.get("budget_window_order_hash"):
        return False
    if not _is_ascii_id(document.get("history_id")):
        return False
    facts = document.get("facts")
    if not isinstance(facts, Mapping):
        return False
    if facts.get("source_preregistrations_exactly_verified") is not True:
        return False
    if facts.get("dual_source_hashes_exactly_pinned") is not True:
        return False
    if facts.get("semantic_study_identity_equivalence_verified") is not False:
        return False
    if facts.get("runtime_consumer_bound") is not False:
        return False
    if facts.get("mounted") is not False or facts.get("synthetic_only") is not True:
        return False
    if not _source_authority_is_locked(document):
        return False
    try:
        return bool(
            source_binding.verify_strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_preregistration_v1(
                document,
                verification_context["history_coverage_registration"],
                verification_context["history_coverage_registration_receipt"],
                verification_context["uncertainty_budget_binding_preregistration"],
                expected_preregistration_hash=expected_preregistration_hash,
                budget_binding_preregistration_verification_context=verification_context[
                    "budget_binding_preregistration_verification_context"
                ],
            )
        )
    except (KeyError, TypeError, ValueError):
        return False


def _registration_core(
    *,
    reviewer_id_hash: str,
    review_process_id_hash: str,
    public_key_sha256: str,
    key_id: str,
) -> dict[str, Any]:
    return {
        "schema_version": REVIEWER_KEY_REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "REGISTERED",
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": SIGNATURE_DOMAIN,
        "key_id": key_id,
        "reviewer_id_sha256": reviewer_id_hash,
        "review_process_id_sha256": review_process_id_hash,
        "public_key_sha256": public_key_sha256,
        "facts": {
            "external_reviewer_identity_verified": False,
            "public_key_material_redacted": True,
            "raw_review_process_redacted": True,
            "raw_reviewer_identity_redacted": True,
            "registration_governance_verified": False,
            "synthetic_only": True,
        },
        "authority": _authority_lock(),
    }


def build_strategy_correlation_semantic_identity_bridge_reviewer_key_registration_v1(
    reviewer_id: Any,
    review_process_id: Any,
    public_key_base64: Any,
) -> dict[str, Any] | None:
    if not _is_ascii_id(reviewer_id) or not _is_ascii_id(review_process_id):
        return None
    public_key = _decode_base64(public_key_base64, 32)
    if public_key is None or Ed25519PublicKey is None:
        return None
    try:
        Ed25519PublicKey.from_public_bytes(public_key)
    except (TypeError, ValueError):
        return None
    public_key_sha256 = hashlib.sha256(public_key).hexdigest()
    key_id = "ed25519:" + _text_digest(SIGNATURE_DOMAIN + ":" + public_key_sha256)[:32]
    return _seal(
        _registration_core(
            reviewer_id_hash=_text_digest(reviewer_id),
            review_process_id_hash=_text_digest(review_process_id),
            public_key_sha256=public_key_sha256,
            key_id=key_id,
        ),
        "registration_hash",
    )


_REGISTRATION_KEYS = set(
    _registration_core(
        reviewer_id_hash="0" * 64,
        review_process_id_hash="0" * 64,
        public_key_sha256="0" * 64,
        key_id="ed25519:" + "0" * 32,
    )
) | {"registration_hash"}


def verify_strategy_correlation_semantic_identity_bridge_reviewer_key_registration_v1(
    document: Any,
    *,
    expected_registration_hash: Any,
) -> bool:
    if not _sealed_exactly(
        document,
        expected_keys=_REGISTRATION_KEYS,
        hash_field="registration_hash",
        expected_hash=expected_registration_hash,
    ):
        return False
    if document.get("schema_version") != REVIEWER_KEY_REGISTRATION_SCHEMA_VERSION:
        return False
    if document.get("static_fingerprint") != STATIC_FINGERPRINT:
        return False
    if document.get("status") != "REGISTERED":
        return False
    if document.get("signature_algorithm") != SIGNATURE_ALGORITHM:
        return False
    if document.get("signature_message_format") != SIGNATURE_MESSAGE_FORMAT:
        return False
    if document.get("signature_domain") != SIGNATURE_DOMAIN:
        return False
    if not _is_ascii_id(document.get("key_id")):
        return False
    if any(
        not _is_hash(document.get(field))
        for field in ("reviewer_id_sha256", "review_process_id_sha256", "public_key_sha256")
    ):
        return False
    expected_core = _registration_core(
        reviewer_id_hash=document["reviewer_id_sha256"],
        review_process_id_hash=document["review_process_id_sha256"],
        public_key_sha256=document["public_key_sha256"],
        key_id=document["key_id"],
    )
    return _seal(expected_core, "registration_hash") == dict(document)


def _bridge_claim_core(
    source_preregistration: Mapping[str, Any],
    *,
    claim_id_sha256: str,
    review_rationale_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": BRIDGE_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CLAIM_BUILT",
        "relationship_claim": RELATIONSHIP_CLAIM,
        "relationship_claim_sha256": _text_digest(RELATIONSHIP_CLAIM),
        "claim_id_sha256": claim_id_sha256,
        "review_rationale_sha256": review_rationale_sha256,
        "source_binding_preregistration_hash": source_preregistration["preregistration_hash"],
        "source_binding_contract_hash": source_preregistration["binding_contract_hash"],
        "source_budget_binding_contract_hash": source_preregistration[
            "budget_binding_contract_hash"
        ],
        "source_static_fingerprint_sha256": _text_digest(
            source_preregistration["static_fingerprint"]
        ),
        "history_id_sha256": _text_digest(source_preregistration["history_id"]),
        "history_study_identity_hash": source_preregistration["history_study_identity_hash"],
        "history_window_order_hash": source_preregistration["history_window_order_hash"],
        "budget_window_order_hash": source_preregistration["budget_window_order_hash"],
        "budget_symbol_order_hash": source_preregistration["budget_symbol_order_hash"],
        "budget_cluster_partition_hash": source_preregistration[
            "budget_cluster_partition_hash"
        ],
        "source_window_order_hashes_equal": False,
        "facts": {
            "distinct_technical_window_identities_bound": True,
            "external_reviewer_identity_verified": False,
            "mounted": False,
            "review_governance_verified": False,
            "reviewer_independence_verified": False,
            "semantic_study_identity_equivalence_verified": False,
            "signed_reviewer_claim_only": True,
            "source_preregistration_exactly_reverified": True,
            "synthetic_only": True,
        },
        "authority": _authority_lock(),
    }


def build_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_claim_v1(
    source_preregistration: Any,
    claim_id: Any,
    review_rationale: Any,
    *,
    expected_source_preregistration_hash: Any,
    source_preregistration_verification_context: Any,
) -> dict[str, Any] | None:
    if not _verify_source_preregistration(
        source_preregistration,
        expected_preregistration_hash=expected_source_preregistration_hash,
        verification_context=source_preregistration_verification_context,
    ):
        return None
    if not _is_ascii_id(claim_id) or not _is_text(review_rationale, minimum=16):
        return None
    return _seal(
        _bridge_claim_core(
            source_preregistration,
            claim_id_sha256=_text_digest(claim_id),
            review_rationale_sha256=_text_digest(review_rationale),
        ),
        "bridge_claim_hash",
    )


_BRIDGE_CLAIM_KEYS = set(
    _bridge_claim_core(
        {
            "preregistration_hash": "0" * 64,
            "binding_contract_hash": "0" * 64,
            "budget_binding_contract_hash": "0" * 64,
            "static_fingerprint": SOURCE_STATIC_FINGERPRINT,
            "history_id": "synthetic-history-v1",
            "history_study_identity_hash": "0" * 64,
            "history_window_order_hash": "1" * 64,
            "budget_window_order_hash": "2" * 64,
            "budget_symbol_order_hash": "3" * 64,
            "budget_cluster_partition_hash": "4" * 64,
        },
        claim_id_sha256="5" * 64,
        review_rationale_sha256="6" * 64,
    )
) | {"bridge_claim_hash"}


def verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_claim_v1(
    document: Any,
    source_preregistration: Any,
    *,
    expected_bridge_claim_hash: Any,
    expected_source_preregistration_hash: Any,
    source_preregistration_verification_context: Any,
) -> bool:
    if not _verify_source_preregistration(
        source_preregistration,
        expected_preregistration_hash=expected_source_preregistration_hash,
        verification_context=source_preregistration_verification_context,
    ):
        return False
    if not _sealed_exactly(
        document,
        expected_keys=_BRIDGE_CLAIM_KEYS,
        hash_field="bridge_claim_hash",
        expected_hash=expected_bridge_claim_hash,
    ):
        return False
    if document.get("schema_version") != BRIDGE_CLAIM_SCHEMA_VERSION:
        return False
    if document.get("static_fingerprint") != STATIC_FINGERPRINT:
        return False
    if document.get("status") != "CLAIM_BUILT":
        return False
    if document.get("relationship_claim") != RELATIONSHIP_CLAIM:
        return False
    if document.get("relationship_claim_sha256") != _text_digest(RELATIONSHIP_CLAIM):
        return False
    if any(
        not _is_hash(document.get(field))
        for field in ("claim_id_sha256", "review_rationale_sha256")
    ):
        return False
    expected_core = _bridge_claim_core(
        source_preregistration,
        claim_id_sha256=document["claim_id_sha256"],
        review_rationale_sha256=document["review_rationale_sha256"],
    )
    return _seal(expected_core, "bridge_claim_hash") == dict(document)


def _unsigned_attestation_core(
    registration: Mapping[str, Any],
    bridge_claim: Mapping[str, Any],
    *,
    review_nonce_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": UNSIGNED_ATTESTATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "AWAITING_DETACHED_SIGNATURE",
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": SIGNATURE_DOMAIN,
        "reviewer_key_registration_hash": registration["registration_hash"],
        "bridge_claim_hash": bridge_claim["bridge_claim_hash"],
        "source_binding_preregistration_hash": bridge_claim[
            "source_binding_preregistration_hash"
        ],
        "key_id": registration["key_id"],
        "public_key_sha256": registration["public_key_sha256"],
        "review_nonce_sha256": review_nonce_sha256,
        "facts": {
            "nonce_uniqueness_verified": False,
            "raw_nonce_redacted": True,
            "replay_durability_verified": False,
            "signature_present": False,
            "synthetic_only": True,
        },
        "authority": _authority_lock(),
    }


def build_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_unsigned_attestation_v1(
    reviewer_key_registration: Any,
    bridge_claim: Any,
    source_preregistration: Any,
    review_nonce: Any,
    *,
    expected_reviewer_key_registration_hash: Any,
    expected_bridge_claim_hash: Any,
    expected_source_preregistration_hash: Any,
    source_preregistration_verification_context: Any,
) -> dict[str, Any] | None:
    if not verify_strategy_correlation_semantic_identity_bridge_reviewer_key_registration_v1(
        reviewer_key_registration,
        expected_registration_hash=expected_reviewer_key_registration_hash,
    ):
        return None
    if not verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_claim_v1(
        bridge_claim,
        source_preregistration,
        expected_bridge_claim_hash=expected_bridge_claim_hash,
        expected_source_preregistration_hash=expected_source_preregistration_hash,
        source_preregistration_verification_context=source_preregistration_verification_context,
    ):
        return None
    if not _is_ascii_id(review_nonce):
        return None
    return _seal(
        _unsigned_attestation_core(
            reviewer_key_registration,
            bridge_claim,
            review_nonce_sha256=_text_digest(review_nonce),
        ),
        "unsigned_attestation_hash",
    )


_UNSIGNED_ATTESTATION_KEYS = set(
    _unsigned_attestation_core(
        {
            "registration_hash": "0" * 64,
            "key_id": "ed25519:" + "0" * 32,
            "public_key_sha256": "1" * 64,
        },
        {
            "bridge_claim_hash": "2" * 64,
            "source_binding_preregistration_hash": "3" * 64,
        },
        review_nonce_sha256="4" * 64,
    )
) | {"unsigned_attestation_hash"}


def verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_unsigned_attestation_v1(
    document: Any,
    reviewer_key_registration: Any,
    bridge_claim: Any,
    source_preregistration: Any,
    review_nonce: Any,
    *,
    expected_unsigned_attestation_hash: Any,
    expected_reviewer_key_registration_hash: Any,
    expected_bridge_claim_hash: Any,
    expected_source_preregistration_hash: Any,
    source_preregistration_verification_context: Any,
) -> bool:
    if not verify_strategy_correlation_semantic_identity_bridge_reviewer_key_registration_v1(
        reviewer_key_registration,
        expected_registration_hash=expected_reviewer_key_registration_hash,
    ):
        return False
    if not verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_claim_v1(
        bridge_claim,
        source_preregistration,
        expected_bridge_claim_hash=expected_bridge_claim_hash,
        expected_source_preregistration_hash=expected_source_preregistration_hash,
        source_preregistration_verification_context=source_preregistration_verification_context,
    ):
        return False
    if not _is_ascii_id(review_nonce):
        return False
    if not _sealed_exactly(
        document,
        expected_keys=_UNSIGNED_ATTESTATION_KEYS,
        hash_field="unsigned_attestation_hash",
        expected_hash=expected_unsigned_attestation_hash,
    ):
        return False
    expected_core = _unsigned_attestation_core(
        reviewer_key_registration,
        bridge_claim,
        review_nonce_sha256=_text_digest(review_nonce),
    )
    return _seal(expected_core, "unsigned_attestation_hash") == dict(document)


def _signed_attestation_core(
    unsigned_attestation: Mapping[str, Any],
    *,
    public_key_base64: str,
    signature_base64: str,
) -> dict[str, Any]:
    return {
        "schema_version": SIGNED_ATTESTATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "DETACHED_SIGNATURE_ATTACHED",
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_domain": SIGNATURE_DOMAIN,
        "unsigned_attestation_hash": unsigned_attestation["unsigned_attestation_hash"],
        "reviewer_key_registration_hash": unsigned_attestation[
            "reviewer_key_registration_hash"
        ],
        "bridge_claim_hash": unsigned_attestation["bridge_claim_hash"],
        "key_id": unsigned_attestation["key_id"],
        "public_key_base64": public_key_base64,
        "signature_base64": signature_base64,
        "facts": {
            "private_key_material_present": False,
            "public_key_and_signature_require_redaction_from_public_evidence": True,
            "signature_present": True,
            "synthetic_only": True,
        },
        "authority": _authority_lock(),
    }


def _signature_is_valid(
    unsigned_attestation_hash: Any,
    public_key_base64: Any,
    signature_base64: Any,
) -> bool:
    if not _is_hash(unsigned_attestation_hash) or Ed25519PublicKey is None:
        return False
    public_key = _decode_base64(public_key_base64, 32)
    signature = _decode_base64(signature_base64, 64)
    if public_key is None or signature is None:
        return False
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature,
            bytes.fromhex(unsigned_attestation_hash),
        )
    except (InvalidSignature, TypeError, ValueError):
        return False
    return True


def assemble_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_attestation_v1(
    unsigned_attestation: Any,
    reviewer_key_registration: Any,
    bridge_claim: Any,
    source_preregistration: Any,
    review_nonce: Any,
    public_key_base64: Any,
    signature_base64: Any,
    *,
    expected_unsigned_attestation_hash: Any,
    expected_reviewer_key_registration_hash: Any,
    expected_bridge_claim_hash: Any,
    expected_source_preregistration_hash: Any,
    source_preregistration_verification_context: Any,
) -> dict[str, Any] | None:
    if not verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_unsigned_attestation_v1(
        unsigned_attestation,
        reviewer_key_registration,
        bridge_claim,
        source_preregistration,
        review_nonce,
        expected_unsigned_attestation_hash=expected_unsigned_attestation_hash,
        expected_reviewer_key_registration_hash=expected_reviewer_key_registration_hash,
        expected_bridge_claim_hash=expected_bridge_claim_hash,
        expected_source_preregistration_hash=expected_source_preregistration_hash,
        source_preregistration_verification_context=source_preregistration_verification_context,
    ):
        return None
    public_key = _decode_base64(public_key_base64, 32)
    if public_key is None:
        return None
    if hashlib.sha256(public_key).hexdigest() != reviewer_key_registration.get(
        "public_key_sha256"
    ):
        return None
    if not _signature_is_valid(
        unsigned_attestation["unsigned_attestation_hash"],
        public_key_base64,
        signature_base64,
    ):
        return None
    return _seal(
        _signed_attestation_core(
            unsigned_attestation,
            public_key_base64=public_key_base64,
            signature_base64=signature_base64,
        ),
        "signed_attestation_hash",
    )


_SIGNED_ATTESTATION_KEYS = set(
    _signed_attestation_core(
        {
            "unsigned_attestation_hash": "0" * 64,
            "reviewer_key_registration_hash": "1" * 64,
            "bridge_claim_hash": "2" * 64,
            "key_id": "ed25519:" + "3" * 32,
        },
        public_key_base64="A" * 44,
        signature_base64="A" * 88,
    )
) | {"signed_attestation_hash"}


def verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_attestation_v1(
    document: Any,
    unsigned_attestation: Any,
    reviewer_key_registration: Any,
    bridge_claim: Any,
    source_preregistration: Any,
    review_nonce: Any,
    *,
    expected_signed_attestation_hash: Any,
    expected_unsigned_attestation_hash: Any,
    expected_reviewer_key_registration_hash: Any,
    expected_bridge_claim_hash: Any,
    expected_source_preregistration_hash: Any,
    source_preregistration_verification_context: Any,
) -> bool:
    if not verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_unsigned_attestation_v1(
        unsigned_attestation,
        reviewer_key_registration,
        bridge_claim,
        source_preregistration,
        review_nonce,
        expected_unsigned_attestation_hash=expected_unsigned_attestation_hash,
        expected_reviewer_key_registration_hash=expected_reviewer_key_registration_hash,
        expected_bridge_claim_hash=expected_bridge_claim_hash,
        expected_source_preregistration_hash=expected_source_preregistration_hash,
        source_preregistration_verification_context=source_preregistration_verification_context,
    ):
        return False
    if not _sealed_exactly(
        document,
        expected_keys=_SIGNED_ATTESTATION_KEYS,
        hash_field="signed_attestation_hash",
        expected_hash=expected_signed_attestation_hash,
    ):
        return False
    public_key = _decode_base64(document.get("public_key_base64"), 32)
    if public_key is None:
        return False
    if hashlib.sha256(public_key).hexdigest() != reviewer_key_registration.get(
        "public_key_sha256"
    ):
        return False
    if not _signature_is_valid(
        unsigned_attestation.get("unsigned_attestation_hash"),
        document.get("public_key_base64"),
        document.get("signature_base64"),
    ):
        return False
    expected_core = _signed_attestation_core(
        unsigned_attestation,
        public_key_base64=document["public_key_base64"],
        signature_base64=document["signature_base64"],
    )
    return _seal(expected_core, "signed_attestation_hash") == dict(document)


def _unknown_evidence() -> dict[str, Any]:
    core = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATE,
        "blockers": ["SIGNED_REVIEW_EVIDENCE_INVALID_OR_INCOMPLETE"],
        "facts": {
            "review_claim_integrity_verified": False,
            "semantic_study_identity_equivalence_verified": False,
            "source_preregistration_reverified": False,
            "synthetic_only": True,
        },
        "authority": _authority_lock(),
    }
    sealed = _seal(core, "evidence_hash")
    if sealed is None:  # pragma: no cover - constant-only structure is serializable.
        raise RuntimeError("constant evidence payload is not serializable")
    return sealed


def _positive_evidence_core(
    signed_attestation: Mapping[str, Any],
    unsigned_attestation: Mapping[str, Any],
    reviewer_key_registration: Mapping[str, Any],
    bridge_claim: Mapping[str, Any],
    source_preregistration: Mapping[str, Any],
) -> dict[str, Any]:
    signature = _decode_base64(signed_attestation["signature_base64"], 64)
    if signature is None:  # pragma: no cover - caller verifies before construction.
        raise ValueError("invalid signature")
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": POSITIVE_STATE,
        "source": {
            "binding_contract_hash": source_preregistration["binding_contract_hash"],
            "budget_cluster_partition_hash": source_preregistration[
                "budget_cluster_partition_hash"
            ],
            "budget_symbol_order_hash": source_preregistration["budget_symbol_order_hash"],
            "budget_window_order_hash": source_preregistration["budget_window_order_hash"],
            "history_study_identity_hash": source_preregistration[
                "history_study_identity_hash"
            ],
            "history_window_order_hash": source_preregistration["history_window_order_hash"],
            "preregistration_hash": source_preregistration["preregistration_hash"],
        },
        "review": {
            "bridge_claim_hash": bridge_claim["bridge_claim_hash"],
            "claim_id_sha256": bridge_claim["claim_id_sha256"],
            "key_id": reviewer_key_registration["key_id"],
            "public_key_sha256": reviewer_key_registration["public_key_sha256"],
            "registration_hash": reviewer_key_registration["registration_hash"],
            "review_nonce_sha256": unsigned_attestation["review_nonce_sha256"],
            "review_process_id_sha256": reviewer_key_registration[
                "review_process_id_sha256"
            ],
            "review_rationale_sha256": bridge_claim["review_rationale_sha256"],
            "reviewer_id_sha256": reviewer_key_registration["reviewer_id_sha256"],
            "signature_sha256": hashlib.sha256(signature).hexdigest(),
            "signed_attestation_hash": signed_attestation["signed_attestation_hash"],
            "unsigned_attestation_hash": unsigned_attestation[
                "unsigned_attestation_hash"
            ],
        },
        "relationship_claim": RELATIONSHIP_CLAIM,
        "blockers": [
            "SEMANTIC_STUDY_IDENTITY_EQUIVALENCE_NOT_VERIFIED",
            "EXTERNAL_REVIEWER_IDENTITY_NOT_VERIFIED",
            "REVIEWER_INDEPENDENCE_NOT_VERIFIED",
            "REVIEW_REGISTRATION_GOVERNANCE_NOT_VERIFIED",
            "NONCE_UNIQUENESS_NOT_VERIFIED",
            "REPLAY_DURABILITY_NOT_VERIFIED",
            "EFFECTIVE_BUDGET_ACTIVATION_NOT_ALLOWED",
            "RUNTIME_CONSUMER_NOT_REGISTERED",
        ],
        "facts": {
            "distinct_technical_window_identities_bound": True,
            "external_reviewer_identity_verified": False,
            "mounted": False,
            "nonce_uniqueness_verified": False,
            "public_key_and_signature_redacted": True,
            "replay_durability_verified": False,
            "review_claim_integrity_verified": True,
            "review_governance_verified": False,
            "reviewer_independence_verified": False,
            "semantic_study_identity_equivalence_verified": False,
            "source_preregistration_reverified": True,
            "synthetic_only": True,
        },
        "authority": _authority_lock(),
    }


def evaluate_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_review_evidence_v1(
    signed_attestation: Any,
    unsigned_attestation: Any,
    reviewer_key_registration: Any,
    bridge_claim: Any,
    source_preregistration: Any,
    review_nonce: Any,
    *,
    expected_signed_attestation_hash: Any,
    expected_unsigned_attestation_hash: Any,
    expected_reviewer_key_registration_hash: Any,
    expected_bridge_claim_hash: Any,
    expected_source_preregistration_hash: Any,
    source_preregistration_verification_context: Any,
) -> dict[str, Any]:
    if not verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_attestation_v1(
        signed_attestation,
        unsigned_attestation,
        reviewer_key_registration,
        bridge_claim,
        source_preregistration,
        review_nonce,
        expected_signed_attestation_hash=expected_signed_attestation_hash,
        expected_unsigned_attestation_hash=expected_unsigned_attestation_hash,
        expected_reviewer_key_registration_hash=expected_reviewer_key_registration_hash,
        expected_bridge_claim_hash=expected_bridge_claim_hash,
        expected_source_preregistration_hash=expected_source_preregistration_hash,
        source_preregistration_verification_context=source_preregistration_verification_context,
    ):
        return _unknown_evidence()
    sealed = _seal(
        _positive_evidence_core(
            signed_attestation,
            unsigned_attestation,
            reviewer_key_registration,
            bridge_claim,
            source_preregistration,
        ),
        "evidence_hash",
    )
    return sealed if sealed is not None else _unknown_evidence()


def verify_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_review_evidence_v1(
    document: Any,
    signed_attestation: Any,
    unsigned_attestation: Any,
    reviewer_key_registration: Any,
    bridge_claim: Any,
    source_preregistration: Any,
    review_nonce: Any,
    *,
    expected_evidence_hash: Any,
    expected_signed_attestation_hash: Any,
    expected_unsigned_attestation_hash: Any,
    expected_reviewer_key_registration_hash: Any,
    expected_bridge_claim_hash: Any,
    expected_source_preregistration_hash: Any,
    source_preregistration_verification_context: Any,
) -> bool:
    expected = evaluate_strategy_correlation_persisted_history_effective_budget_semantic_identity_bridge_signed_review_evidence_v1(
        signed_attestation,
        unsigned_attestation,
        reviewer_key_registration,
        bridge_claim,
        source_preregistration,
        review_nonce,
        expected_signed_attestation_hash=expected_signed_attestation_hash,
        expected_unsigned_attestation_hash=expected_unsigned_attestation_hash,
        expected_reviewer_key_registration_hash=expected_reviewer_key_registration_hash,
        expected_bridge_claim_hash=expected_bridge_claim_hash,
        expected_source_preregistration_hash=expected_source_preregistration_hash,
        source_preregistration_verification_context=source_preregistration_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and _is_hash(expected_evidence_hash)
        and document.get("evidence_hash") == expected_evidence_hash
        and expected.get("evidence_hash") == expected_evidence_hash
        and dict(document) == expected
    )
