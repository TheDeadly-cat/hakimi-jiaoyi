"""Domain-separated signed provider receipt evidence for ADR0413."""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application import (
    witness_ownership_state_provider_preregistration_v1 as preregistration,
)
from exchange_terminal.application import witness_ownership_state_service
from exchange_terminal.application.ports import (
    witness_ownership_state_store_v1 as witness_ownership_state_store,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1,
    load_canonical_ed25519_public_key_v1,
)


SIGNED_RECEIPT_SCHEMA_VERSION = (
    "witness-ownership-state-provider-signed-receipt-v1"
)
VERIFICATION_EVIDENCE_SCHEMA_VERSION = (
    "witness-ownership-state-provider-signed-receipt-verification-evidence-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-provider-signed-receipt-v1-lock-1"
)
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_MESSAGE_FORMAT = (
    "STRICT_CANONICAL_DOMAIN_SEPARATED_SHA256_DIGEST_BYTES_V1"
)
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.witness-ownership.provider-receipt.v1"
)

_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_KEYS = (
    "current_admission_allowed",
    "live_order_allowed",
    "migration_allowed",
    "paper_authorized",
    "provider_activation_allowed",
    "provider_identity_trust_allowed",
    "runtime_gate_activation_allowed",
    "witness_ownership_state_trust_allowed",
    "writer_allowed",
)
_SOURCE_TRUTH_BLOCKERS = (
    "PROVIDER_ORGANIZATION_IDENTITY_UNVERIFIED",
    "PROVIDER_KEY_CONTROL_CONTINUITY_UNVERIFIED",
    "PROVIDER_IMPLEMENTATION_UNVERIFIED",
    "EXTERNAL_PROVIDER_CONFORMANCE_UNVERIFIED",
    "DURABLE_ATOMIC_COMPARE_CONSUME_AND_ADVANCE_UNVERIFIED",
    "LINEARIZABLE_READ_AFTER_WRITE_UNVERIFIED",
    "ROLLBACK_RESISTANCE_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_PATTERN.fullmatch(value) is not None


def _require_hash(name: str, value: Any) -> str:
    if not _is_hash(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _locked_authority() -> dict[str, bool]:
    return {key: False for key in _AUTHORITY_KEYS}


def _decode_public_key(value: Any):
    if type(value) is not str or not value:
        raise ValueError("public_key_spki_base64 must be non-empty")
    spki_bytes = decode_canonical_base64_v1(
        value, "public_key_spki_base64"
    )
    public_key = load_canonical_ed25519_public_key_v1(spki_bytes)
    return spki_bytes, public_key


def _decode_signature(value: Any) -> bytes:
    if type(value) is not str or not value:
        raise ValueError("signature_base64 must be non-empty")
    signature = decode_canonical_base64_v1(value, "signature_base64")
    if len(signature) != 64:
        raise ValueError("Ed25519 signature must be exactly 64 bytes")
    return signature


def _validate_exact_context(
    consumer_evaluation_document: Any,
    budget_v11_document: Any,
    command: Any,
    provider_result: Any,
    preregistration_document: Any,
    *,
    expected_consumer_evaluation_hash: Any,
    consumer_verify_kwargs: Any,
    preregistration_build_kwargs: Any,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    evaluation_hash = _require_hash(
        "expected_consumer_evaluation_hash",
        expected_consumer_evaluation_hash,
    )
    if (
        type(consumer_evaluation_document) is not dict
        or type(budget_v11_document) is not dict
        or type(command)
        is not witness_ownership_state_store.WitnessOwnershipCompareConsumeAndAdvanceCommandV1
        or type(provider_result)
        is not witness_ownership_state_store.WitnessOwnershipCompareConsumeAndAdvanceResultV1
        or type(preregistration_document) is not dict
        or type(consumer_verify_kwargs) is not dict
        or type(preregistration_build_kwargs) is not dict
        or "expected_evaluation_hash" in consumer_verify_kwargs
    ):
        raise ValueError("signed receipt context has an inexact type")
    if not preregistration.verify_witness_ownership_state_provider_preregistration_v1(
        preregistration_document,
        **dict(preregistration_build_kwargs),
    ):
        raise ValueError("provider preregistration is not exact")
    if not witness_ownership_state_service.verify_witness_ownership_state_persistence_consumer_v1(
        consumer_evaluation_document,
        budget_v11_document,
        command,
        provider_result,
        expected_evaluation_hash=evaluation_hash,
        **dict(consumer_verify_kwargs),
    ):
        raise ValueError("ADR0412 consumer evaluation is not exact")
    identity = preregistration_document.get("identity")
    receipt = provider_result.receipt_document
    if (
        not isinstance(identity, Mapping)
        or not isinstance(receipt, Mapping)
        or consumer_evaluation_document.get("status") != "UNKNOWN"
        or consumer_evaluation_document.get("admission_status") != "BLOCKED"
        or provider_result.outcome
        is not witness_ownership_state_store.WitnessOwnershipProviderOutcomeV1.ADVANCED
        or command.namespace_preregistration_hash
        != preregistration_document.get("preregistration_hash")
        or provider_result.registry_id != identity.get("registry_id")
        or consumer_verify_kwargs.get("expected_registry_id")
        != provider_result.registry_id
        or receipt.get("receipt_claim_hash") is None
        or not _is_hash(receipt.get("receipt_claim_hash"))
    ):
        raise ValueError("signed receipt context binding drifted")
    return identity, receipt


def build_witness_ownership_provider_receipt_signature_message_hash_v1(
    consumer_evaluation_document: Any,
    budget_v11_document: Any,
    command: Any,
    provider_result: Any,
    preregistration_document: Any,
    *,
    expected_consumer_evaluation_hash: Any,
    consumer_verify_kwargs: Any,
    preregistration_build_kwargs: Any,
) -> str:
    _, receipt = _validate_exact_context(
        consumer_evaluation_document,
        budget_v11_document,
        command,
        provider_result,
        preregistration_document,
        expected_consumer_evaluation_hash=(
            expected_consumer_evaluation_hash
        ),
        consumer_verify_kwargs=consumer_verify_kwargs,
        preregistration_build_kwargs=preregistration_build_kwargs,
    )
    return strict_canonical_hash(
        {
            "signature_domain": SIGNATURE_DOMAIN,
            "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
            "preregistration_hash": preregistration_document[
                "preregistration_hash"
            ],
            "consumer_evaluation_hash": expected_consumer_evaluation_hash,
            "command_hash": command.command_hash,
            "consumption_key": command.consumption_key,
            "receipt_claim_hash": receipt["receipt_claim_hash"],
            "registry_id": provider_result.registry_id,
            "returned_registry_revision": (
                provider_result.returned_registry_revision
            ),
            "returned_state_hash": provider_result.returned_state_hash,
        }
    )


def build_signed_witness_ownership_state_provider_receipt_v1(
    consumer_evaluation_document: Any,
    budget_v11_document: Any,
    command: Any,
    provider_result: Any,
    preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_consumer_evaluation_hash: Any,
    consumer_verify_kwargs: Any,
    preregistration_build_kwargs: Any,
) -> dict[str, Any]:
    message_hash = (
        build_witness_ownership_provider_receipt_signature_message_hash_v1(
            consumer_evaluation_document,
            budget_v11_document,
            command,
            provider_result,
            preregistration_document,
            expected_consumer_evaluation_hash=(
                expected_consumer_evaluation_hash
            ),
            consumer_verify_kwargs=consumer_verify_kwargs,
            preregistration_build_kwargs=preregistration_build_kwargs,
        )
    )
    spki_bytes, _ = _decode_public_key(public_key_spki_base64)
    _decode_signature(signature_base64)
    receipt = provider_result.receipt_document
    body = {
        "schema_version": SIGNED_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "SIGNED_CANDIDATE",
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signature_domain": SIGNATURE_DOMAIN,
        "signature_message_format": SIGNATURE_MESSAGE_FORMAT,
        "signature_message_hash": message_hash,
        "signature_base64": signature_base64,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": sha256(spki_bytes).hexdigest(),
        "preregistration_hash": preregistration_document[
            "preregistration_hash"
        ],
        "consumer_evaluation_hash": expected_consumer_evaluation_hash,
        "command_hash": command.command_hash,
        "receipt_claim_hash": receipt["receipt_claim_hash"],
        "registry_id": provider_result.registry_id,
        "returned_registry_revision": (
            provider_result.returned_registry_revision
        ),
        "returned_state_hash": provider_result.returned_state_hash,
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(body, "signed_receipt_hash")


def evaluate_signed_witness_ownership_state_provider_receipt_v1(
    signed_receipt_document: Any,
    consumer_evaluation_document: Any,
    budget_v11_document: Any,
    command: Any,
    provider_result: Any,
    preregistration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_signed_receipt_hash: Any,
    expected_consumer_evaluation_hash: Any,
    consumer_verify_kwargs: Any,
    preregistration_build_kwargs: Any,
) -> dict[str, Any]:
    context_exact = False
    signed_document_exact = False
    key_hash_matches = False
    cryptographic_signature_verified = False
    message_hash: str | None = None
    public_key_hash: str | None = None
    signed_receipt_hash: str | None = None
    receipt_claim_hash: str | None = None
    try:
        expected_signed_receipt_hash = _require_hash(
            "expected_signed_receipt_hash", expected_signed_receipt_hash
        )
        expected = build_signed_witness_ownership_state_provider_receipt_v1(
            consumer_evaluation_document,
            budget_v11_document,
            command,
            provider_result,
            preregistration_document,
            public_key_spki_base64=public_key_spki_base64,
            signature_base64=signature_base64,
            expected_consumer_evaluation_hash=(
                expected_consumer_evaluation_hash
            ),
            consumer_verify_kwargs=consumer_verify_kwargs,
            preregistration_build_kwargs=preregistration_build_kwargs,
        )
        context_exact = True
        signed_receipt_hash = expected["signed_receipt_hash"]
        signed_document_exact = (
            signed_receipt_hash == expected_signed_receipt_hash
            and strict_json_contract_equal(signed_receipt_document, expected)
        )
        spki_bytes, public_key = _decode_public_key(
            public_key_spki_base64
        )
        signature = _decode_signature(signature_base64)
        public_key_hash = sha256(spki_bytes).hexdigest()
        key_hash_matches = (
            public_key_hash
            == preregistration_document["identity"][
                "public_key_spki_sha256"
            ]
        )
        message_hash = expected["signature_message_hash"]
        receipt_claim_hash = expected["receipt_claim_hash"]
        try:
            public_key.verify(signature, bytes.fromhex(message_hash))
            cryptographic_signature_verified = True
        except (InvalidSignature, ValueError):
            cryptographic_signature_verified = False
    except (KeyError, TypeError, ValueError):
        pass

    local_signature_verified = (
        context_exact
        and signed_document_exact
        and key_hash_matches
        and cryptographic_signature_verified
    )
    dynamic_blockers: list[str] = []
    if not context_exact:
        dynamic_blockers.append("SIGNED_RECEIPT_CONTEXT_NOT_EXACT")
    if not signed_document_exact:
        dynamic_blockers.append("SIGNED_RECEIPT_DOCUMENT_NOT_EXACT")
    if not key_hash_matches:
        dynamic_blockers.append("PREREGISTERED_PUBLIC_KEY_HASH_MISMATCH")
    if not cryptographic_signature_verified:
        dynamic_blockers.append("ED25519_RECEIPT_SIGNATURE_INVALID")

    body = {
        "schema_version": VERIFICATION_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_signature_verified else "BLOCK",
        "admission_status": "BLOCKED",
        "receipt_status": (
            "SIGNED_PROVIDER_RECEIPT_CANDIDATE_BLOCKED"
            if local_signature_verified
            else "UNKNOWN"
        ),
        "decision": (
            "PREREGISTERED_KEY_RECEIPT_SIGNATURE_VERIFIED_EXTERNAL_SOURCE_"
            "TRUTH_STILL_BLOCKED"
            if local_signature_verified
            else "SIGNED_PROVIDER_RECEIPT_UNKNOWN_OR_INVALID"
        ),
        "blockers": dynamic_blockers + list(_SOURCE_TRUTH_BLOCKERS),
        "checks": [
            {"name": "signed_receipt_context_exact", "ok": context_exact},
            {
                "name": "signed_receipt_document_exact",
                "ok": signed_document_exact,
            },
            {
                "name": "public_key_hash_matches_preregistration",
                "ok": key_hash_matches,
            },
            {
                "name": "ed25519_receipt_signature_verified",
                "ok": cryptographic_signature_verified,
            },
        ],
        "facts": {
            "adr0412_consumer_evaluation_exact": context_exact,
            "signed_receipt_document_exact": signed_document_exact,
            "preregistered_key_hash_matched": key_hash_matches,
            "cryptographic_receipt_signature_verified": (
                cryptographic_signature_verified
            ),
            "provider_key_possession_observed": local_signature_verified,
            "provider_receipt_signature_verified": local_signature_verified,
            "provider_organization_identity_verified": False,
            "provider_key_control_continuity_verified": False,
            "provider_implementation_verified": False,
            "external_provider_conformance_verified": False,
            "atomic_operation_source_truth_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_after_write_verified": False,
            "rollback_resistance_verified": False,
            "witness_ownership_state_persistence_verified": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "network_accessed": False,
            "execution_verified": False,
            "profitability_proven": False,
        },
        "source": {
            "preregistration_hash": (
                preregistration_document.get("preregistration_hash")
                if isinstance(preregistration_document, Mapping)
                else None
            ),
            "consumer_evaluation_hash": (
                expected_consumer_evaluation_hash
                if _is_hash(expected_consumer_evaluation_hash)
                else None
            ),
            "signature_message_hash": message_hash,
            "receipt_claim_hash": receipt_claim_hash,
            "public_key_spki_sha256": public_key_hash,
            "signed_receipt_hash": signed_receipt_hash,
        },
        "authority": _locked_authority(),
        "redaction": {
            "raw_public_key_redacted": True,
            "raw_signature_redacted": True,
            "raw_provider_credentials_embedded": False,
            "raw_budget_documents_embedded": False,
            "raw_ownership_documents_embedded": False,
        },
        "limitations": [
            "A valid local signature proves only possession of the preregistered private key for this domain-separated message.",
            "It does not prove provider organization identity, key continuity, provider implementation, external conformance, atomicity, durability, linearizability, rollback resistance, or persistence.",
            "No current, runtime, paper, live, writer, migration, execution, profitability, or trading authority is granted.",
        ],
    }
    return seal_strict_canonical_document(body, "verification_evidence_hash")


def verify_signed_witness_ownership_state_provider_receipt_evidence_v1(
    evidence_document: Any,
    signed_receipt_document: Any,
    consumer_evaluation_document: Any,
    budget_v11_document: Any,
    command: Any,
    provider_result: Any,
    preregistration_document: Any,
    *,
    expected_verification_evidence_hash: Any,
    **evaluation_kwargs: Any,
) -> bool:
    if not _is_hash(expected_verification_evidence_hash):
        return False
    expected = evaluate_signed_witness_ownership_state_provider_receipt_v1(
        signed_receipt_document,
        consumer_evaluation_document,
        budget_v11_document,
        command,
        provider_result,
        preregistration_document,
        **evaluation_kwargs,
    )
    return (
        expected["verification_evidence_hash"]
        == expected_verification_evidence_hash
        and strict_json_contract_equal(evidence_document, expected)
    )


__all__ = [
    "SIGNATURE_ALGORITHM",
    "SIGNATURE_DOMAIN",
    "SIGNATURE_MESSAGE_FORMAT",
    "SIGNED_RECEIPT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_EVIDENCE_SCHEMA_VERSION",
    "build_signed_witness_ownership_state_provider_receipt_v1",
    "build_witness_ownership_provider_receipt_signature_message_hash_v1",
    "evaluate_signed_witness_ownership_state_provider_receipt_v1",
    "verify_signed_witness_ownership_state_provider_receipt_evidence_v1",
]
