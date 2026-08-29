from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from cryptography.exceptions import InvalidSignature

from . import strategy_correlation_cluster_effective_bet_budget_v7 as budget_v7
from .strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1 as _decode_canonical_base64,
    load_canonical_ed25519_public_key_v1 as _load_ed25519_public_key,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


STATIC_FINGERPRINT = (
    "20260824-atomic-head-clock-counter-effective-budget-v8-synthetic-lock-1"
)
STORE_PROVIDER_SCHEMA_VERSION = (
    "strategy-correlation-atomic-head-store-provider-preregistration-v1"
)
ATOMIC_STATE_SCHEMA_VERSION = "strategy-correlation-atomic-head-state-v1"
COMMIT_CLAIM_SCHEMA_VERSION = "strategy-correlation-atomic-head-commit-claim-v1"
SIGNED_RECEIPT_SCHEMA_VERSION = (
    "strategy-correlation-atomic-head-signed-commit-receipt-v1"
)
COMMIT_EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-atomic-head-commit-signature-evidence-v1"
)
BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v8"

_MAX_INTEGER = 9_999_999_999_999_999
_SIGNATURE_DOMAIN = "hakimi.strategy-correlation.atomic-head-store.v1"
_SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"
_LIMITATIONS = [
    "ATOMIC_STORE_PROVIDER_IDENTITY_UNVERIFIED",
    "ATOMIC_STORE_IMPLEMENTATION_UNVERIFIED",
    "ATOMIC_COMPARE_AND_SWAP_PERSISTENCE_UNVERIFIED",
    "CRASH_RECOVERY_AND_DURABILITY_UNVERIFIED",
    "CLOCK_PROVIDER_AND_TIME_TRUTH_UNVERIFIED",
    "SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
]


def _locked_authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "atomic_state_source_trust_allowed": False,
        "clock_source_trust_allowed": False,
        "snapshot_source_trust_allowed": False,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return deepcopy(value)


def _require_identifier(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 160
        or value != value.strip()
        or any(character.isspace() for character in value)
    ):
        raise ValueError(f"{field} must be a compact nonempty identifier")
    return value


def _require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < 0 or value > _MAX_INTEGER:
        raise ValueError(f"{field} is outside the allowed range")
    return value


def _require_sha256(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _document_sha256(value: Any) -> str | None:
    try:
        return _require_sha256(value, "document hash")
    except ValueError:
        return None


def _document_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _check(check_id: str, passed: bool) -> dict[str, str]:
    return {"check_id": check_id, "status": "PASS" if passed else "BLOCK"}


def _blockers(checks: list[dict[str, str]]) -> list[str]:
    return [item["check_id"] for item in checks if item["status"] != "PASS"]


def build_atomic_head_store_provider_preregistration_v1(
    *,
    provider_id: Any,
    key_id: Any,
    public_key_spki_sha256: Any,
    trust_domain: Any,
    account_scope_hash: Any,
    store_epoch_hash: Any,
    implementation_claim_sha256: Any,
) -> dict[str, Any]:
    document = {
        "schema_version": STORE_PROVIDER_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "ATOMIC_HEAD_STORE_PROVIDER_PREREGISTERED_"
            "IDENTITY_IMPLEMENTATION_DURABILITY_AND_SOURCE_TRUTH_UNVERIFIED"
        ),
        "identity": {
            "provider_id": _require_identifier(provider_id, "provider_id"),
            "key_id": _require_identifier(key_id, "key_id"),
            "public_key_spki_sha256": _require_sha256(
                public_key_spki_sha256,
                "public_key_spki_sha256",
            ),
            "trust_domain": _require_identifier(trust_domain, "trust_domain"),
            "account_scope_hash": _require_sha256(
                account_scope_hash,
                "account_scope_hash",
            ),
            "store_epoch_hash": _require_sha256(
                store_epoch_hash,
                "store_epoch_hash",
            ),
            "implementation_claim_sha256": _require_sha256(
                implementation_claim_sha256,
                "implementation_claim_sha256",
            ),
        },
        "compare_and_swap_contract": {
            "operation": "EXPECTED_PREVIOUS_STATE_HASH_SWAP",
            "state_revision_rule": "EXACT_PREVIOUS_PLUS_ONE",
            "commit_index_rule": "EXACT_PREVIOUS_PLUS_ONE",
            "clock_counter_rule": "EXACT_PREVIOUS_PLUS_ONE",
        },
        "signature_contract": {
            "algorithm": "ED25519",
            "domain": _SIGNATURE_DOMAIN,
            "message_format": _SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "local_preregistration_complete": True,
            "provider_identity_verified": False,
            "provider_key_possession_verified": False,
            "provider_implementation_verified": False,
            "atomic_compare_and_swap_verified": False,
            "durability_verified": False,
            "crash_recovery_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "atomic_store_provider_hash")


def verify_atomic_head_store_provider_preregistration_v1(
    document: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        rebuilt = build_atomic_head_store_provider_preregistration_v1(**build_kwargs)
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, rebuilt)


def build_atomic_head_state_v1(
    atomic_store_provider_document: Any,
    *,
    atomic_store_provider_kwargs: Any,
    policy_hash: Any,
    state_revision: Any,
    commit_index: Any,
    clock_counter: Any,
    clock_evidence_hash: Any,
    snapshot_state_hash: Any,
    snapshot_claim_hash: Any,
    transition_hash: Any,
) -> dict[str, Any]:
    provider_kwargs = _require_mapping(
        atomic_store_provider_kwargs,
        "atomic_store_provider_kwargs",
    )
    if not verify_atomic_head_store_provider_preregistration_v1(
        atomic_store_provider_document,
        **provider_kwargs,
    ):
        raise ValueError("atomic store provider preregistration is not exact")
    provider = _mapping(atomic_store_provider_document)
    identity = _mapping(provider.get("identity"))
    document = {
        "schema_version": ATOMIC_STATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "decision": (
            "LOCAL_ATOMIC_HEAD_STATE_CANDIDATE_"
            "STORE_IDENTITY_DURABILITY_AND_SOURCE_TRUTH_UNVERIFIED"
        ),
        "source": {
            "atomic_store_provider_hash": _require_sha256(
                provider.get("atomic_store_provider_hash"),
                "atomic_store_provider_hash",
            ),
            "account_scope_hash": _require_sha256(
                identity.get("account_scope_hash"),
                "account_scope_hash",
            ),
            "store_epoch_hash": _require_sha256(
                identity.get("store_epoch_hash"),
                "store_epoch_hash",
            ),
            "policy_hash": _require_sha256(policy_hash, "policy_hash"),
        },
        "state": {
            "state_revision": _require_int(state_revision, "state_revision"),
            "commit_index": _require_int(commit_index, "commit_index"),
            "clock_counter": _require_int(clock_counter, "clock_counter"),
            "clock_evidence_hash": _require_sha256(
                clock_evidence_hash,
                "clock_evidence_hash",
            ),
            "snapshot_state_hash": _require_sha256(
                snapshot_state_hash,
                "snapshot_state_hash",
            ),
            "snapshot_claim_hash": _require_sha256(
                snapshot_claim_hash,
                "snapshot_claim_hash",
            ),
            "transition_hash": _require_sha256(
                transition_hash,
                "transition_hash",
            ),
        },
        "facts": {
            "local_state_shape_exact": True,
            "store_provider_preregistration_exact": True,
            "atomic_compare_and_swap_verified": False,
            "durability_verified": False,
            "crash_recovery_verified": False,
            "external_current_head_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "atomic_head_state_hash")


def verify_atomic_head_state_v1(
    document: Any,
    atomic_store_provider_document: Any,
    *,
    expected_atomic_head_state_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_atomic_head_state_hash,
            "expected_atomic_head_state_hash",
        )
        rebuilt = build_atomic_head_state_v1(
            atomic_store_provider_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("atomic_head_state_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_atomic_head_commit_claim_v1(
    previous_atomic_head_state_document: Any,
    atomic_store_provider_document: Any,
    *,
    expected_previous_atomic_head_state_hash: Any,
    previous_atomic_head_state_build_kwargs: Any,
    operation_id_hash: Any,
    next_clock_evidence_hash: Any,
    next_snapshot_state_hash: Any,
    next_snapshot_claim_hash: Any,
    next_transition_hash: Any,
) -> dict[str, Any]:
    previous_hash = _require_sha256(
        expected_previous_atomic_head_state_hash,
        "expected_previous_atomic_head_state_hash",
    )
    previous_kwargs = _require_mapping(
        previous_atomic_head_state_build_kwargs,
        "previous_atomic_head_state_build_kwargs",
    )
    if not verify_atomic_head_state_v1(
        previous_atomic_head_state_document,
        atomic_store_provider_document,
        expected_atomic_head_state_hash=previous_hash,
        **previous_kwargs,
    ):
        raise ValueError("previous atomic head state is not exact")

    previous = _mapping(previous_atomic_head_state_document)
    previous_source = _mapping(previous.get("source"))
    previous_state = _mapping(previous.get("state"))
    previous_revision = _require_int(
        previous_state.get("state_revision"),
        "previous state_revision",
    )
    previous_commit_index = _require_int(
        previous_state.get("commit_index"),
        "previous commit_index",
    )
    previous_clock_counter = _require_int(
        previous_state.get("clock_counter"),
        "previous clock_counter",
    )
    next_state = build_atomic_head_state_v1(
        atomic_store_provider_document,
        atomic_store_provider_kwargs=previous_kwargs[
            "atomic_store_provider_kwargs"
        ],
        policy_hash=previous_source.get("policy_hash"),
        state_revision=previous_revision + 1,
        commit_index=previous_commit_index + 1,
        clock_counter=previous_clock_counter + 1,
        clock_evidence_hash=next_clock_evidence_hash,
        snapshot_state_hash=next_snapshot_state_hash,
        snapshot_claim_hash=next_snapshot_claim_hash,
        transition_hash=next_transition_hash,
    )
    next_payload = _mapping(next_state.get("state"))

    document = {
        "schema_version": COMMIT_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "ATOMIC_HEAD_COMMIT_CLAIM_UNSIGNED_"
            "STORE_IDENTITY_ATOMICITY_DURABILITY_AND_SOURCE_TRUTH_UNVERIFIED"
        ),
        "source": {
            "atomic_store_provider_hash": _require_sha256(
                previous_source.get("atomic_store_provider_hash"),
                "atomic_store_provider_hash",
            ),
            "account_scope_hash": _require_sha256(
                previous_source.get("account_scope_hash"),
                "account_scope_hash",
            ),
            "store_epoch_hash": _require_sha256(
                previous_source.get("store_epoch_hash"),
                "store_epoch_hash",
            ),
            "policy_hash": _require_sha256(
                previous_source.get("policy_hash"),
                "policy_hash",
            ),
        },
        "operation": {
            "operation_id_hash": _require_sha256(
                operation_id_hash,
                "operation_id_hash",
            ),
            "operation": "EXPECTED_PREVIOUS_STATE_HASH_SWAP",
            "expected_previous_state_hash": previous_hash,
            "next_state_hash": next_state["atomic_head_state_hash"],
        },
        "transition_summary": {
            "previous_state_revision": previous_revision,
            "next_state_revision": next_payload["state_revision"],
            "previous_commit_index": previous_commit_index,
            "next_commit_index": next_payload["commit_index"],
            "previous_clock_counter": previous_clock_counter,
            "next_clock_counter": next_payload["clock_counter"],
            "next_clock_evidence_hash": next_payload["clock_evidence_hash"],
            "next_snapshot_state_hash": next_payload["snapshot_state_hash"],
            "next_snapshot_claim_hash": next_payload["snapshot_claim_hash"],
            "next_transition_hash": next_payload["transition_hash"],
        },
        "next_state_candidate": next_state,
        "signature_contract": {
            "algorithm": "ED25519",
            "domain": _SIGNATURE_DOMAIN,
            "message_format": _SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "previous_state_exact": True,
            "state_revision_increment_exact": True,
            "commit_index_increment_exact": True,
            "clock_counter_increment_exact": True,
            "atomic_store_signature_verified": False,
            "atomic_compare_and_swap_verified": False,
            "durability_verified": False,
            "crash_recovery_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "atomic_commit_claim_hash")


def verify_atomic_head_commit_claim_v1(
    document: Any,
    previous_atomic_head_state_document: Any,
    atomic_store_provider_document: Any,
    *,
    expected_atomic_commit_claim_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_atomic_commit_claim_hash,
            "expected_atomic_commit_claim_hash",
        )
        rebuilt = build_atomic_head_commit_claim_v1(
            previous_atomic_head_state_document,
            atomic_store_provider_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("atomic_commit_claim_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_signed_atomic_head_commit_receipt_v1(
    atomic_commit_claim_document: Any,
    previous_atomic_head_state_document: Any,
    atomic_store_provider_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_atomic_commit_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_atomic_commit_claim_hash,
        "expected_atomic_commit_claim_hash",
    )
    claim_kwargs = _require_mapping(claim_build_kwargs, "claim_build_kwargs")
    if not verify_atomic_head_commit_claim_v1(
        atomic_commit_claim_document,
        previous_atomic_head_state_document,
        atomic_store_provider_document,
        expected_atomic_commit_claim_hash=claim_hash,
        **claim_kwargs,
    ):
        raise ValueError("atomic head commit claim is not exact")

    spki_bytes = _decode_canonical_base64(
        public_key_spki_base64,
        "public_key_spki_base64",
    )
    _load_ed25519_public_key(spki_bytes)
    signature_bytes = _decode_canonical_base64(signature_base64, "signature_base64")
    if len(signature_bytes) != 64:
        raise ValueError("Ed25519 signature must be 64 bytes")
    provider = _mapping(atomic_store_provider_document)
    identity = _mapping(provider.get("identity"))
    spki_hash = hashlib.sha256(spki_bytes).hexdigest()
    if spki_hash != identity.get("public_key_spki_sha256"):
        raise ValueError("public key hash does not match atomic store preregistration")

    document = {
        "schema_version": SIGNED_RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "atomic_commit_claim_hash": claim_hash,
        "atomic_store_provider_hash": _require_sha256(
            provider.get("atomic_store_provider_hash"),
            "atomic_store_provider_hash",
        ),
        "signature_algorithm": "ED25519",
        "signature_domain": _SIGNATURE_DOMAIN,
        "signature_message_format": _SIGNATURE_MESSAGE_FORMAT,
        "public_key_spki_base64": public_key_spki_base64,
        "public_key_spki_sha256": spki_hash,
        "signature_base64": signature_base64,
        "signature_sha256": hashlib.sha256(signature_bytes).hexdigest(),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "signed_atomic_commit_receipt_hash")


def verify_signed_atomic_head_commit_receipt_v1(
    document: Any,
    atomic_commit_claim_document: Any,
    previous_atomic_head_state_document: Any,
    atomic_store_provider_document: Any,
    *,
    expected_signed_atomic_commit_receipt_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_signed_atomic_commit_receipt_hash,
            "expected_signed_atomic_commit_receipt_hash",
        )
        rebuilt = build_signed_atomic_head_commit_receipt_v1(
            atomic_commit_claim_document,
            previous_atomic_head_state_document,
            atomic_store_provider_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("signed_atomic_commit_receipt_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_signed_atomic_head_commit_receipt_v1(
    signed_atomic_commit_receipt_document: Any,
    atomic_commit_claim_document: Any,
    previous_atomic_head_state_document: Any,
    atomic_store_provider_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_atomic_commit_claim_hash: Any,
    expected_signed_atomic_commit_receipt_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_atomic_commit_claim_hash,
        "expected_atomic_commit_claim_hash",
    )
    signed_hash = _require_sha256(
        expected_signed_atomic_commit_receipt_hash,
        "expected_signed_atomic_commit_receipt_hash",
    )
    signed_exact = verify_signed_atomic_head_commit_receipt_v1(
        signed_atomic_commit_receipt_document,
        atomic_commit_claim_document,
        previous_atomic_head_state_document,
        atomic_store_provider_document,
        expected_signed_atomic_commit_receipt_hash=signed_hash,
        public_key_spki_base64=public_key_spki_base64,
        signature_base64=signature_base64,
        expected_atomic_commit_claim_hash=claim_hash,
        claim_build_kwargs=claim_build_kwargs,
    )
    signature_verified = False
    key_hash_matches = False
    try:
        spki_bytes = _decode_canonical_base64(
            public_key_spki_base64,
            "public_key_spki_base64",
        )
        signature_bytes = _decode_canonical_base64(
            signature_base64,
            "signature_base64",
        )
        public_key = _load_ed25519_public_key(spki_bytes)
        provider = _mapping(atomic_store_provider_document)
        identity = _mapping(provider.get("identity"))
        key_hash_matches = (
            hashlib.sha256(spki_bytes).hexdigest()
            == identity.get("public_key_spki_sha256")
        )
        if signed_exact and key_hash_matches:
            public_key.verify(signature_bytes, bytes.fromhex(claim_hash))
            signature_verified = True
    except (InvalidSignature, TypeError, ValueError):
        signature_verified = False

    claim = _mapping(atomic_commit_claim_document)
    source = _mapping(claim.get("source"))
    operation = _mapping(claim.get("operation"))
    transition = _mapping(claim.get("transition_summary"))
    local_signature_pass = bool(signed_exact and key_hash_matches and signature_verified)
    checks = [
        _check("SIGNED_ATOMIC_COMMIT_RECEIPT_EXACT", signed_exact),
        _check("ATOMIC_STORE_KEY_HASH_MATCHES_PREREGISTRATION", key_hash_matches),
        _check("ATOMIC_STORE_SIGNATURE_VERIFIED", signature_verified),
    ]
    document = {
        "schema_version": COMMIT_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_signature_pass else "BLOCKED",
        "decision": (
            "PREREGISTERED_ATOMIC_STORE_KEY_SIGNATURE_OBSERVED_"
            "IDENTITY_ATOMICITY_DURABILITY_AND_SOURCE_TRUTH_UNVERIFIED"
            if local_signature_pass
            else "BLOCK_ATOMIC_HEAD_COMMIT_SIGNATURE_CONTRACT"
        ),
        "source": {
            "atomic_store_provider_hash": _document_sha256(
                source.get("atomic_store_provider_hash")
            ),
            "atomic_commit_claim_hash": claim_hash,
            "signed_atomic_commit_receipt_hash": signed_hash,
            "atomic_store_public_key_spki_sha256": _document_sha256(
                _mapping(signed_atomic_commit_receipt_document).get(
                    "public_key_spki_sha256"
                )
            ),
            "account_scope_hash": _document_sha256(
                source.get("account_scope_hash")
            ),
            "store_epoch_hash": _document_sha256(source.get("store_epoch_hash")),
            "policy_hash": _document_sha256(source.get("policy_hash")),
        },
        "commit_summary": {
            "operation_id_hash": _document_sha256(
                operation.get("operation_id_hash")
            ),
            "expected_previous_state_hash": _document_sha256(
                operation.get("expected_previous_state_hash")
            ),
            "next_state_hash": _document_sha256(operation.get("next_state_hash")),
            "next_state_revision": _document_int(
                transition.get("next_state_revision")
            ),
            "next_commit_index": _document_int(transition.get("next_commit_index")),
            "next_clock_counter": _document_int(
                transition.get("next_clock_counter")
            ),
            "next_clock_evidence_hash": _document_sha256(
                transition.get("next_clock_evidence_hash")
            ),
            "next_snapshot_state_hash": _document_sha256(
                transition.get("next_snapshot_state_hash")
            ),
            "next_snapshot_claim_hash": _document_sha256(
                transition.get("next_snapshot_claim_hash")
            ),
            "next_transition_hash": _document_sha256(
                transition.get("next_transition_hash")
            ),
        },
        "checks": checks,
        "facts": {
            "atomic_commit_claim_exact": signed_exact,
            "signed_atomic_commit_receipt_exact": signed_exact,
            "atomic_store_key_hash_matches_preregistration": key_hash_matches,
            "cryptographic_signature_verified": signature_verified,
            "preregistered_atomic_store_key_signature_verified": local_signature_pass,
            "state_revision_increment_arithmetic_verified": signed_exact,
            "commit_index_increment_arithmetic_verified": signed_exact,
            "clock_counter_increment_arithmetic_verified": signed_exact,
            "atomic_store_provider_identity_verified": False,
            "atomic_store_implementation_verified": False,
            "atomic_compare_and_swap_verified": False,
            "durability_verified": False,
            "crash_recovery_verified": False,
            "raw_public_key_redacted": True,
            "raw_signature_redacted": True,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "atomic_commit_evidence_hash")


def verify_signed_atomic_head_commit_evidence_v1(
    document: Any,
    *args: Any,
    expected_atomic_commit_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_atomic_commit_evidence_hash,
            "expected_atomic_commit_evidence_hash",
        )
        rebuilt = evaluate_signed_atomic_head_commit_receipt_v1(*args, **kwargs)
    except Exception:
        return False
    return (
        rebuilt.get("atomic_commit_evidence_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_strategy_correlation_cluster_effective_bet_budget_v8(
    atomic_commit_evidence_document: Any,
    signed_atomic_commit_receipt_document: Any,
    atomic_commit_claim_document: Any,
    previous_atomic_head_state_document: Any,
    atomic_store_provider_document: Any,
    clock_evidence_document: Any,
    signed_clock_attestation_document: Any,
    clock_claim_document: Any,
    clock_provider_preregistration_document: Any,
    transition_document: Any,
    previous_snapshot_state_document: Any,
    policy_document: Any,
    snapshot_evidence_document: Any,
    signed_snapshot_document: Any,
    snapshot_claim_document: Any,
    snapshot_provider_preregistration_document: Any,
    correlation_preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    expected_atomic_commit_evidence_hash: Any,
    atomic_commit_evaluation_kwargs: Any,
    expected_clock_evidence_hash: Any,
    clock_evaluation_kwargs: Any,
    expected_transition_hash: Any,
    transition_evaluation_kwargs: Any,
    expected_snapshot_evidence_hash: Any,
    snapshot_evaluation_kwargs: Any,
    strata_registration: Any = None,
    strata_gate: Any = None,
    complete_link_gate: Any = None,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = 45.0,
    risk_increasing: Any = True,
    positions_after: Any = None,
    risk_reduction_transition: Any = None,
) -> dict[str, Any]:
    atomic_evidence_hash = _require_sha256(
        expected_atomic_commit_evidence_hash,
        "expected_atomic_commit_evidence_hash",
    )
    clock_evidence_hash = _require_sha256(
        expected_clock_evidence_hash,
        "expected_clock_evidence_hash",
    )
    transition_hash = _require_sha256(
        expected_transition_hash,
        "expected_transition_hash",
    )
    snapshot_evidence_hash = _require_sha256(
        expected_snapshot_evidence_hash,
        "expected_snapshot_evidence_hash",
    )
    atomic_kwargs = _require_mapping(
        atomic_commit_evaluation_kwargs,
        "atomic_commit_evaluation_kwargs",
    )
    clock_kwargs = _require_mapping(
        clock_evaluation_kwargs,
        "clock_evaluation_kwargs",
    )
    transition_kwargs = _require_mapping(
        transition_evaluation_kwargs,
        "transition_evaluation_kwargs",
    )
    snapshot_kwargs = _require_mapping(
        snapshot_evaluation_kwargs,
        "snapshot_evaluation_kwargs",
    )

    atomic_evidence_exact = verify_signed_atomic_head_commit_evidence_v1(
        atomic_commit_evidence_document,
        signed_atomic_commit_receipt_document,
        atomic_commit_claim_document,
        previous_atomic_head_state_document,
        atomic_store_provider_document,
        expected_atomic_commit_evidence_hash=atomic_evidence_hash,
        **atomic_kwargs,
    )
    atomic_evidence = _mapping(atomic_commit_evidence_document)
    atomic_facts = _mapping(atomic_evidence.get("facts"))
    atomic_source = _mapping(atomic_evidence.get("source"))
    atomic_summary = _mapping(atomic_evidence.get("commit_summary"))
    atomic_claim = _mapping(atomic_commit_claim_document)
    current_atomic_state = _mapping(atomic_claim.get("next_state_candidate"))
    current_atomic_payload = _mapping(current_atomic_state.get("state"))
    atomic_signature_pass = bool(
        atomic_evidence_exact
        and atomic_evidence.get("status") == "PASS"
        and atomic_facts.get(
            "preregistered_atomic_store_key_signature_verified"
        )
        is True
    )
    derived_snapshot_state_hash = _document_sha256(
        current_atomic_payload.get("snapshot_state_hash")
    )

    if atomic_signature_pass and derived_snapshot_state_hash is not None:
        try:
            v7_result = (
                budget_v7.evaluate_strategy_correlation_cluster_effective_bet_budget_v7(
                    clock_evidence_document,
                    signed_clock_attestation_document,
                    clock_claim_document,
                    clock_provider_preregistration_document,
                    transition_document,
                    previous_snapshot_state_document,
                    policy_document,
                    snapshot_evidence_document,
                    signed_snapshot_document,
                    snapshot_claim_document,
                    snapshot_provider_preregistration_document,
                    correlation_preregistration,
                    correlation_matrix,
                    complete_link_audit,
                    expected_clock_evidence_hash=clock_evidence_hash,
                    clock_evaluation_kwargs=clock_kwargs,
                    expected_transition_hash=transition_hash,
                    transition_evaluation_kwargs=transition_kwargs,
                    expected_current_state_hash=derived_snapshot_state_hash,
                    expected_snapshot_evidence_hash=snapshot_evidence_hash,
                    snapshot_evaluation_kwargs=snapshot_kwargs,
                    strata_registration=strata_registration,
                    strata_gate=strata_gate,
                    complete_link_gate=complete_link_gate,
                    proposed_symbol=proposed_symbol,
                    proposed_notional=proposed_notional,
                    proposed_direction=proposed_direction,
                    max_cluster_gross_pct=max_cluster_gross_pct,
                    risk_increasing=risk_increasing,
                    positions_after=positions_after,
                    risk_reduction_transition=risk_reduction_transition,
                )
            )
        except Exception:
            v7_result = {}
    else:
        v7_result = {}

    v7_document = _mapping(v7_result)
    v7_source = _mapping(v7_document.get("source"))
    v7_clock_summary = _mapping(v7_document.get("clock_summary"))
    v7_authority = _mapping(v7_document.get("authority"))
    policy = _mapping(policy_document)
    policy_source = _mapping(policy.get("source"))
    atomic_provider = _mapping(atomic_store_provider_document)
    atomic_identity = _mapping(atomic_provider.get("identity"))

    current_state_exact = bool(
        atomic_signature_pass
        and atomic_summary.get("next_state_hash")
        == current_atomic_state.get("atomic_head_state_hash")
        and atomic_summary.get("next_state_revision")
        == current_atomic_payload.get("state_revision")
        and atomic_summary.get("next_commit_index")
        == current_atomic_payload.get("commit_index")
        and atomic_summary.get("next_clock_counter")
        == current_atomic_payload.get("clock_counter")
    )
    atomic_subject_binding_exact = bool(
        current_state_exact
        and current_atomic_state.get("source", {}).get("policy_hash")
        == policy.get("policy_hash")
        and current_atomic_payload.get("clock_evidence_hash")
        == clock_evidence_hash
        and current_atomic_payload.get("snapshot_state_hash")
        == _mapping(transition_document).get("next_state_hash")
        and current_atomic_payload.get("snapshot_claim_hash")
        == v7_source.get("snapshot_claim_hash")
        and current_atomic_payload.get("transition_hash")
        == transition_hash
    )
    clock_counter_binding_exact = bool(
        current_state_exact
        and current_atomic_payload.get("clock_counter")
        == v7_clock_summary.get("clock_counter")
    )
    account_scope_binding_exact = bool(
        atomic_signature_pass
        and atomic_source.get("account_scope_hash")
        == atomic_identity.get("account_scope_hash")
        == policy_source.get("account_scope_hash")
    )
    v7_local_pass = bool(
        v7_document.get("status") == "PASS"
        and v7_document.get("blockers") == []
    )
    v7_authority_locked = bool(
        v7_document.get("admission_status") == "BLOCKED"
        and v7_authority.get("current_admission_allowed") is False
        and v7_authority.get("paper_authorized") is False
        and v7_authority.get("live_order_allowed") is False
    )

    checks = [
        _check("SIGNED_ATOMIC_COMMIT_EVIDENCE_EXACT", atomic_evidence_exact),
        _check("SIGNED_ATOMIC_STORE_KEY_SIGNATURE_PASS", atomic_signature_pass),
        _check("CURRENT_ATOMIC_STATE_EXACT", current_state_exact),
        _check("ATOMIC_STATE_BUDGET_SUBJECT_BINDING_EXACT", atomic_subject_binding_exact),
        _check("CLOCK_COUNTER_CONTINUITY_BINDING_EXACT", clock_counter_binding_exact),
        _check("ATOMIC_STORE_ACCOUNT_SCOPE_BINDING_EXACT", account_scope_binding_exact),
        _check("V7_EFFECTIVE_BUDGET_PASS", v7_local_pass),
        _check("V7_ADMISSION_AUTHORITY_REMAINS_BLOCKED", v7_authority_locked),
    ]
    local_budget_pass = not _blockers(checks)
    status = "PASS" if local_budget_pass else "BLOCKED"
    document = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "admission_status": "BLOCKED",
        "decision": (
            "PASS_SIGNED_ATOMIC_HEAD_AND_CLOCK_COUNTER_BOUND_EFFECTIVE_BUDGET_"
            "STORE_ATOMICITY_DURABILITY_AND_SOURCE_TRUTH_UNVERIFIED"
            if local_budget_pass
            else "BLOCK_ATOMIC_HEAD_CLOCK_COUNTER_OR_EFFECTIVE_BUDGET_CONTRACT"
        ),
        "source": {
            "atomic_store_provider_hash": _document_sha256(
                atomic_source.get("atomic_store_provider_hash")
            ),
            "atomic_commit_claim_hash": _document_sha256(
                atomic_source.get("atomic_commit_claim_hash")
            ),
            "signed_atomic_commit_receipt_hash": _document_sha256(
                atomic_source.get("signed_atomic_commit_receipt_hash")
            ),
            "atomic_commit_evidence_hash": atomic_evidence_hash,
            "atomic_head_state_hash": _document_sha256(
                current_atomic_state.get("atomic_head_state_hash")
            ),
            "clock_evidence_hash": clock_evidence_hash,
            "policy_hash": _document_sha256(v7_source.get("policy_hash")),
            "transition_hash": transition_hash,
            "snapshot_state_hash": derived_snapshot_state_hash,
            "snapshot_claim_hash": _document_sha256(
                v7_source.get("snapshot_claim_hash")
            ),
            "v7_budget_hash": _document_sha256(v7_document.get("budget_v7_hash")),
        },
        "atomic_state_summary": {
            "state_revision": _document_int(
                current_atomic_payload.get("state_revision")
            ),
            "commit_index": _document_int(current_atomic_payload.get("commit_index")),
            "clock_counter": _document_int(current_atomic_payload.get("clock_counter")),
        },
        "clock_summary": deepcopy(v7_document.get("clock_summary")),
        "snapshot_summary": deepcopy(v7_document.get("snapshot_summary")),
        "budget_summary": deepcopy(v7_document.get("budget_summary")),
        "checks": checks,
        "facts": {
            "atomic_commit_evidence_exact": atomic_evidence_exact,
            "preregistered_atomic_store_key_signature_verified": (
                atomic_signature_pass
            ),
            "atomic_state_bound_to_budget_subject": atomic_subject_binding_exact,
            "clock_counter_transition_arithmetic_verified": bool(
                atomic_facts.get("clock_counter_increment_arithmetic_verified")
                is True
            ),
            "clock_counter_bound_to_signed_clock_evidence": (
                clock_counter_binding_exact
            ),
            "caller_expected_snapshot_state_hash_input_accepted": False,
            "caller_clock_counter_input_accepted": False,
            "predecessor_admission_authority_preserved_blocked": (
                v7_authority_locked
            ),
            "atomic_store_provider_identity_verified": False,
            "atomic_store_implementation_verified": False,
            "atomic_compare_and_swap_verified": False,
            "atomic_current_head_persistence_verified": False,
            "durability_verified": False,
            "crash_recovery_verified": False,
            "trusted_evaluation_clock_verified": False,
            "time_source_truth_verified": False,
            "snapshot_source_truth_verified": False,
            "runtime_gate_integrated": False,
            "execution_verified": False,
            "profitability_proven": False,
            "raw_public_key_embedded": False,
            "raw_signature_embedded": False,
            "raw_positions_embedded": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "budget_v8_hash")


def verify_strategy_correlation_cluster_effective_bet_budget_v8(
    document: Any,
    *args: Any,
    expected_budget_v8_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_budget_v8_hash,
            "expected_budget_v8_hash",
        )
        rebuilt = evaluate_strategy_correlation_cluster_effective_bet_budget_v8(
            *args,
            **kwargs,
        )
    except Exception:
        return False
    return (
        rebuilt.get("budget_v8_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )
