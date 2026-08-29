from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from cryptography.exceptions import InvalidSignature

from . import strategy_correlation_cluster_effective_bet_budget_v8 as budget_v8
from .strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1 as _decode_canonical_base64,
    load_canonical_ed25519_public_key_v1 as _load_ed25519_public_key,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


STATIC_FINGERPRINT = (
    "20260824-authenticated-latest-head-effective-budget-v9-synthetic-lock-1"
)
CHECKPOINT_SCHEMA_VERSION = (
    "strategy-correlation-authenticated-latest-head-checkpoint-v1"
)
READ_CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-authenticated-latest-head-read-claim-v1"
)
SIGNED_READ_SCHEMA_VERSION = (
    "strategy-correlation-authenticated-latest-head-signed-read-v1"
)
READ_EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-authenticated-latest-head-read-signature-evidence-v1"
)
BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v9"

_MAX_INTEGER = 9_999_999_999_999_999
_SIGNATURE_DOMAIN = "hakimi.strategy-correlation.authenticated-latest-head.v1"
_SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"
_LIMITATIONS = [
    "LATEST_HEAD_SOURCE_TRUTH_UNVERIFIED",
    "ATOMIC_STORE_PROVIDER_IDENTITY_UNVERIFIED",
    "ATOMIC_STORE_IMPLEMENTATION_UNVERIFIED",
    "ATOMIC_COMPARE_AND_SWAP_PERSISTENCE_UNVERIFIED",
    "DURABILITY_AND_CRASH_RECOVERY_UNVERIFIED",
    "CLOCK_AND_SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
]


def _locked_authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "latest_head_source_trust_allowed": False,
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


def build_authenticated_latest_head_checkpoint_v1(
    atomic_store_provider_document: Any,
    *,
    atomic_store_provider_kwargs: Any,
    checkpoint_revision: Any,
    predecessor_checkpoint_hash: Any,
    minimum_commit_index: Any,
    minimum_clock_counter: Any,
    minimum_state_revision: Any,
    accepted_atomic_head_state_hash: Any,
    accepted_atomic_commit_evidence_hash: Any,
) -> dict[str, Any]:
    provider_kwargs = _require_mapping(
        atomic_store_provider_kwargs,
        "atomic_store_provider_kwargs",
    )
    if not budget_v8.verify_atomic_head_store_provider_preregistration_v1(
        atomic_store_provider_document,
        **provider_kwargs,
    ):
        raise ValueError("atomic store provider preregistration is not exact")
    provider = _mapping(atomic_store_provider_document)
    identity = _mapping(provider.get("identity"))
    document = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "decision": (
            "LOCAL_LATEST_HEAD_ROLLBACK_FLOOR_CANDIDATE_"
            "SOURCE_TRUTH_AND_DURABILITY_UNVERIFIED"
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
        },
        "checkpoint": {
            "checkpoint_revision": _require_int(
                checkpoint_revision,
                "checkpoint_revision",
            ),
            "predecessor_checkpoint_hash": _require_sha256(
                predecessor_checkpoint_hash,
                "predecessor_checkpoint_hash",
            ),
            "minimum_commit_index": _require_int(
                minimum_commit_index,
                "minimum_commit_index",
            ),
            "minimum_clock_counter": _require_int(
                minimum_clock_counter,
                "minimum_clock_counter",
            ),
            "minimum_state_revision": _require_int(
                minimum_state_revision,
                "minimum_state_revision",
            ),
            "accepted_atomic_head_state_hash": _require_sha256(
                accepted_atomic_head_state_hash,
                "accepted_atomic_head_state_hash",
            ),
            "accepted_atomic_commit_evidence_hash": _require_sha256(
                accepted_atomic_commit_evidence_hash,
                "accepted_atomic_commit_evidence_hash",
            ),
        },
        "facts": {
            "local_checkpoint_shape_exact": True,
            "rollback_floor_preregistered": True,
            "latest_head_source_truth_verified": False,
            "atomic_store_provider_identity_verified": False,
            "atomic_store_implementation_verified": False,
            "durability_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "latest_head_checkpoint_hash")


def verify_authenticated_latest_head_checkpoint_v1(
    document: Any,
    atomic_store_provider_document: Any,
    *,
    expected_latest_head_checkpoint_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_latest_head_checkpoint_hash,
            "expected_latest_head_checkpoint_hash",
        )
        rebuilt = build_authenticated_latest_head_checkpoint_v1(
            atomic_store_provider_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("latest_head_checkpoint_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_authenticated_latest_head_read_claim_v1(
    latest_head_checkpoint_document: Any,
    atomic_store_provider_document: Any,
    *,
    expected_latest_head_checkpoint_hash: Any,
    latest_head_checkpoint_build_kwargs: Any,
    query_id_hash: Any,
    query_clock_evidence_hash: Any,
    query_evaluated_at_unix_ms: Any,
    observed_atomic_commit_evidence_hash: Any,
    observed_atomic_head_state_hash: Any,
    observed_commit_index: Any,
    observed_clock_counter: Any,
    observed_state_revision: Any,
) -> dict[str, Any]:
    checkpoint_hash = _require_sha256(
        expected_latest_head_checkpoint_hash,
        "expected_latest_head_checkpoint_hash",
    )
    checkpoint_kwargs = _require_mapping(
        latest_head_checkpoint_build_kwargs,
        "latest_head_checkpoint_build_kwargs",
    )
    if not verify_authenticated_latest_head_checkpoint_v1(
        latest_head_checkpoint_document,
        atomic_store_provider_document,
        expected_latest_head_checkpoint_hash=checkpoint_hash,
        **checkpoint_kwargs,
    ):
        raise ValueError("latest head checkpoint is not exact")

    checkpoint_document = _mapping(latest_head_checkpoint_document)
    checkpoint_source = _mapping(checkpoint_document.get("source"))
    checkpoint = _mapping(checkpoint_document.get("checkpoint"))
    checkpoint_revision = _require_int(
        checkpoint.get("checkpoint_revision"),
        "checkpoint checkpoint_revision",
    )
    minimum_commit_index = _require_int(
        checkpoint.get("minimum_commit_index"),
        "checkpoint minimum_commit_index",
    )
    minimum_clock_counter = _require_int(
        checkpoint.get("minimum_clock_counter"),
        "checkpoint minimum_clock_counter",
    )
    minimum_state_revision = _require_int(
        checkpoint.get("minimum_state_revision"),
        "checkpoint minimum_state_revision",
    )
    accepted_state_hash = _require_sha256(
        checkpoint.get("accepted_atomic_head_state_hash"),
        "accepted_atomic_head_state_hash",
    )
    accepted_evidence_hash = _require_sha256(
        checkpoint.get("accepted_atomic_commit_evidence_hash"),
        "accepted_atomic_commit_evidence_hash",
    )

    commit_index = _require_int(observed_commit_index, "observed_commit_index")
    clock_counter = _require_int(observed_clock_counter, "observed_clock_counter")
    state_revision = _require_int(observed_state_revision, "observed_state_revision")
    state_hash = _require_sha256(
        observed_atomic_head_state_hash,
        "observed_atomic_head_state_hash",
    )
    evidence_hash = _require_sha256(
        observed_atomic_commit_evidence_hash,
        "observed_atomic_commit_evidence_hash",
    )
    commit_delta = commit_index - minimum_commit_index
    if commit_delta < 0:
        raise ValueError("observed commit index is below rollback floor")
    if clock_counter != minimum_clock_counter + commit_delta:
        raise ValueError("clock counter delta must equal commit index delta")
    if state_revision != minimum_state_revision + commit_delta:
        raise ValueError("state revision delta must equal commit index delta")
    if commit_delta == 0 and (
        state_hash != accepted_state_hash or evidence_hash != accepted_evidence_hash
    ):
        raise ValueError("same-index read must match accepted checkpoint hashes")
    if commit_delta > 0 and (
        state_hash == accepted_state_hash or evidence_hash == accepted_evidence_hash
    ):
        raise ValueError("advanced read must advance state and evidence hashes")

    next_checkpoint = build_authenticated_latest_head_checkpoint_v1(
        atomic_store_provider_document,
        atomic_store_provider_kwargs=checkpoint_kwargs[
            "atomic_store_provider_kwargs"
        ],
        checkpoint_revision=checkpoint_revision + 1,
        predecessor_checkpoint_hash=checkpoint_hash,
        minimum_commit_index=commit_index,
        minimum_clock_counter=clock_counter,
        minimum_state_revision=state_revision,
        accepted_atomic_head_state_hash=state_hash,
        accepted_atomic_commit_evidence_hash=evidence_hash,
    )
    document = {
        "schema_version": READ_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "LATEST_HEAD_READ_CLAIM_UNSIGNED_"
            "PROVIDER_IDENTITY_LATESTNESS_AND_DURABILITY_UNVERIFIED"
        ),
        "source": {
            "atomic_store_provider_hash": _require_sha256(
                checkpoint_source.get("atomic_store_provider_hash"),
                "atomic_store_provider_hash",
            ),
            "account_scope_hash": _require_sha256(
                checkpoint_source.get("account_scope_hash"),
                "account_scope_hash",
            ),
            "store_epoch_hash": _require_sha256(
                checkpoint_source.get("store_epoch_hash"),
                "store_epoch_hash",
            ),
            "previous_checkpoint_hash": checkpoint_hash,
        },
        "query": {
            "query_id_hash": _require_sha256(query_id_hash, "query_id_hash"),
            "clock_evidence_hash": _require_sha256(
                query_clock_evidence_hash,
                "query_clock_evidence_hash",
            ),
            "evaluated_at_unix_ms": _require_int(
                query_evaluated_at_unix_ms,
                "query_evaluated_at_unix_ms",
            ),
        },
        "observation": {
            "atomic_commit_evidence_hash": evidence_hash,
            "atomic_head_state_hash": state_hash,
            "commit_index": commit_index,
            "clock_counter": clock_counter,
            "state_revision": state_revision,
            "commit_delta_from_floor": commit_delta,
        },
        "next_checkpoint_hash": next_checkpoint["latest_head_checkpoint_hash"],
        "next_checkpoint_candidate": next_checkpoint,
        "signature_contract": {
            "algorithm": "ED25519",
            "domain": _SIGNATURE_DOMAIN,
            "message_format": _SIGNATURE_MESSAGE_FORMAT,
        },
        "facts": {
            "previous_checkpoint_exact": True,
            "commit_index_rollback_floor_satisfied": True,
            "clock_counter_delta_matches_commit_delta": True,
            "state_revision_delta_matches_commit_delta": True,
            "same_index_equivocation_rejected": True,
            "latest_head_read_signature_verified": False,
            "latest_head_source_truth_verified": False,
            "durability_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "latest_head_read_claim_hash")


def verify_authenticated_latest_head_read_claim_v1(
    document: Any,
    latest_head_checkpoint_document: Any,
    atomic_store_provider_document: Any,
    *,
    expected_latest_head_read_claim_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_latest_head_read_claim_hash,
            "expected_latest_head_read_claim_hash",
        )
        rebuilt = build_authenticated_latest_head_read_claim_v1(
            latest_head_checkpoint_document,
            atomic_store_provider_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("latest_head_read_claim_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_signed_authenticated_latest_head_read_v1(
    latest_head_read_claim_document: Any,
    latest_head_checkpoint_document: Any,
    atomic_store_provider_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_latest_head_read_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_latest_head_read_claim_hash,
        "expected_latest_head_read_claim_hash",
    )
    claim_kwargs = _require_mapping(claim_build_kwargs, "claim_build_kwargs")
    if not verify_authenticated_latest_head_read_claim_v1(
        latest_head_read_claim_document,
        latest_head_checkpoint_document,
        atomic_store_provider_document,
        expected_latest_head_read_claim_hash=claim_hash,
        **claim_kwargs,
    ):
        raise ValueError("latest head read claim is not exact")

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
        "schema_version": SIGNED_READ_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "latest_head_read_claim_hash": claim_hash,
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
    return seal_strict_canonical_document(document, "signed_latest_head_read_hash")


def verify_signed_authenticated_latest_head_read_v1(
    document: Any,
    latest_head_read_claim_document: Any,
    latest_head_checkpoint_document: Any,
    atomic_store_provider_document: Any,
    *,
    expected_signed_latest_head_read_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_signed_latest_head_read_hash,
            "expected_signed_latest_head_read_hash",
        )
        rebuilt = build_signed_authenticated_latest_head_read_v1(
            latest_head_read_claim_document,
            latest_head_checkpoint_document,
            atomic_store_provider_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("signed_latest_head_read_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_signed_authenticated_latest_head_read_v1(
    signed_latest_head_read_document: Any,
    latest_head_read_claim_document: Any,
    latest_head_checkpoint_document: Any,
    atomic_store_provider_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    expected_latest_head_read_claim_hash: Any,
    expected_signed_latest_head_read_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_latest_head_read_claim_hash,
        "expected_latest_head_read_claim_hash",
    )
    signed_hash = _require_sha256(
        expected_signed_latest_head_read_hash,
        "expected_signed_latest_head_read_hash",
    )
    signed_exact = verify_signed_authenticated_latest_head_read_v1(
        signed_latest_head_read_document,
        latest_head_read_claim_document,
        latest_head_checkpoint_document,
        atomic_store_provider_document,
        expected_signed_latest_head_read_hash=signed_hash,
        public_key_spki_base64=public_key_spki_base64,
        signature_base64=signature_base64,
        expected_latest_head_read_claim_hash=claim_hash,
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

    claim = _mapping(latest_head_read_claim_document)
    source = _mapping(claim.get("source"))
    query = _mapping(claim.get("query"))
    observation = _mapping(claim.get("observation"))
    local_signature_pass = bool(signed_exact and key_hash_matches and signature_verified)
    checks = [
        _check("SIGNED_LATEST_HEAD_READ_EXACT", signed_exact),
        _check("LATEST_HEAD_READ_KEY_HASH_MATCHES", key_hash_matches),
        _check("LATEST_HEAD_READ_SIGNATURE_VERIFIED", signature_verified),
    ]
    document = {
        "schema_version": READ_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if local_signature_pass else "BLOCKED",
        "decision": (
            "PREREGISTERED_STORE_KEY_LATEST_HEAD_READ_SIGNATURE_OBSERVED_"
            "PROVIDER_IDENTITY_LATESTNESS_AND_DURABILITY_UNVERIFIED"
            if local_signature_pass
            else "BLOCK_AUTHENTICATED_LATEST_HEAD_READ_SIGNATURE_CONTRACT"
        ),
        "source": {
            "atomic_store_provider_hash": _document_sha256(
                source.get("atomic_store_provider_hash")
            ),
            "account_scope_hash": _document_sha256(
                source.get("account_scope_hash")
            ),
            "store_epoch_hash": _document_sha256(source.get("store_epoch_hash")),
            "previous_checkpoint_hash": _document_sha256(
                source.get("previous_checkpoint_hash")
            ),
            "latest_head_read_claim_hash": claim_hash,
            "signed_latest_head_read_hash": signed_hash,
            "next_checkpoint_hash": _document_sha256(
                claim.get("next_checkpoint_hash")
            ),
        },
        "query": {
            "query_id_hash": _document_sha256(query.get("query_id_hash")),
            "clock_evidence_hash": _document_sha256(
                query.get("clock_evidence_hash")
            ),
            "evaluated_at_unix_ms": _document_int(
                query.get("evaluated_at_unix_ms")
            ),
        },
        "observation": {
            "atomic_commit_evidence_hash": _document_sha256(
                observation.get("atomic_commit_evidence_hash")
            ),
            "atomic_head_state_hash": _document_sha256(
                observation.get("atomic_head_state_hash")
            ),
            "commit_index": _document_int(observation.get("commit_index")),
            "clock_counter": _document_int(observation.get("clock_counter")),
            "state_revision": _document_int(observation.get("state_revision")),
            "commit_delta_from_floor": _document_int(
                observation.get("commit_delta_from_floor")
            ),
        },
        "checks": checks,
        "facts": {
            "latest_head_read_claim_exact": signed_exact,
            "signed_latest_head_read_exact": signed_exact,
            "preregistered_store_key_signature_verified": local_signature_pass,
            "rollback_floor_arithmetic_verified": signed_exact,
            "latest_head_source_truth_verified": False,
            "atomic_store_provider_identity_verified": False,
            "atomic_store_implementation_verified": False,
            "durability_verified": False,
            "raw_public_key_redacted": True,
            "raw_signature_redacted": True,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "latest_head_read_evidence_hash")


def verify_signed_authenticated_latest_head_read_evidence_v1(
    document: Any,
    *args: Any,
    expected_latest_head_read_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_latest_head_read_evidence_hash,
            "expected_latest_head_read_evidence_hash",
        )
        rebuilt = evaluate_signed_authenticated_latest_head_read_v1(*args, **kwargs)
    except Exception:
        return False
    return (
        rebuilt.get("latest_head_read_evidence_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_strategy_correlation_cluster_effective_bet_budget_v9(
    latest_head_read_evidence_document: Any,
    signed_latest_head_read_document: Any,
    latest_head_read_claim_document: Any,
    latest_head_checkpoint_document: Any,
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
    expected_latest_head_read_evidence_hash: Any,
    latest_head_read_evaluation_kwargs: Any,
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
    read_evidence_hash = _require_sha256(
        expected_latest_head_read_evidence_hash,
        "expected_latest_head_read_evidence_hash",
    )
    read_kwargs = _require_mapping(
        latest_head_read_evaluation_kwargs,
        "latest_head_read_evaluation_kwargs",
    )
    read_evidence_exact = verify_signed_authenticated_latest_head_read_evidence_v1(
        latest_head_read_evidence_document,
        signed_latest_head_read_document,
        latest_head_read_claim_document,
        latest_head_checkpoint_document,
        atomic_store_provider_document,
        expected_latest_head_read_evidence_hash=read_evidence_hash,
        **read_kwargs,
    )
    read_evidence = _mapping(latest_head_read_evidence_document)
    read_facts = _mapping(read_evidence.get("facts"))
    read_source = _mapping(read_evidence.get("source"))
    read_query = _mapping(read_evidence.get("query"))
    read_observation = _mapping(read_evidence.get("observation"))
    read_claim = _mapping(latest_head_read_claim_document)
    next_checkpoint = _mapping(read_claim.get("next_checkpoint_candidate"))
    read_signature_pass = bool(
        read_evidence_exact
        and read_evidence.get("status") == "PASS"
        and read_facts.get("preregistered_store_key_signature_verified") is True
    )

    if read_signature_pass:
        try:
            v8_result = (
                budget_v8.evaluate_strategy_correlation_cluster_effective_bet_budget_v8(
                    atomic_commit_evidence_document,
                    signed_atomic_commit_receipt_document,
                    atomic_commit_claim_document,
                    previous_atomic_head_state_document,
                    atomic_store_provider_document,
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
                    expected_atomic_commit_evidence_hash=expected_atomic_commit_evidence_hash,
                    atomic_commit_evaluation_kwargs=atomic_commit_evaluation_kwargs,
                    expected_clock_evidence_hash=expected_clock_evidence_hash,
                    clock_evaluation_kwargs=clock_evaluation_kwargs,
                    expected_transition_hash=expected_transition_hash,
                    transition_evaluation_kwargs=transition_evaluation_kwargs,
                    expected_snapshot_evidence_hash=expected_snapshot_evidence_hash,
                    snapshot_evaluation_kwargs=snapshot_evaluation_kwargs,
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
            v8_result = {}
    else:
        v8_result = {}

    v8_document = _mapping(v8_result)
    v8_source = _mapping(v8_document.get("source"))
    v8_atomic_summary = _mapping(v8_document.get("atomic_state_summary"))
    v8_clock_summary = _mapping(v8_document.get("clock_summary"))
    v8_authority = _mapping(v8_document.get("authority"))
    atomic_provider = _mapping(atomic_store_provider_document)
    atomic_identity = _mapping(atomic_provider.get("identity"))

    observed_head_binding_exact = bool(
        read_signature_pass
        and read_observation.get("atomic_commit_evidence_hash")
        == v8_source.get("atomic_commit_evidence_hash")
        and read_observation.get("atomic_head_state_hash")
        == v8_source.get("atomic_head_state_hash")
        and read_observation.get("commit_index")
        == v8_atomic_summary.get("commit_index")
        and read_observation.get("clock_counter")
        == v8_atomic_summary.get("clock_counter")
        and read_observation.get("state_revision")
        == v8_atomic_summary.get("state_revision")
    )
    query_clock_binding_exact = bool(
        read_signature_pass
        and read_query.get("clock_evidence_hash")
        == v8_source.get("clock_evidence_hash")
        and read_query.get("evaluated_at_unix_ms")
        == v8_clock_summary.get("evaluated_at_unix_ms")
    )
    store_binding_exact = bool(
        read_signature_pass
        and read_source.get("atomic_store_provider_hash")
        == v8_source.get("atomic_store_provider_hash")
        == atomic_provider.get("atomic_store_provider_hash")
        and read_source.get("account_scope_hash")
        == atomic_identity.get("account_scope_hash")
    )
    next_checkpoint_exact = bool(
        read_signature_pass
        and read_source.get("next_checkpoint_hash")
        == next_checkpoint.get("latest_head_checkpoint_hash")
    )
    v8_local_pass = bool(
        v8_document.get("status") == "PASS"
        and v8_document.get("blockers") == []
    )
    v8_authority_locked = bool(
        v8_document.get("admission_status") == "BLOCKED"
        and v8_authority.get("current_admission_allowed") is False
        and v8_authority.get("paper_authorized") is False
        and v8_authority.get("live_order_allowed") is False
    )
    checks = [
        _check("SIGNED_LATEST_HEAD_READ_EVIDENCE_EXACT", read_evidence_exact),
        _check("SIGNED_LATEST_HEAD_READ_KEY_SIGNATURE_PASS", read_signature_pass),
        _check("LATEST_HEAD_OBSERVATION_BINDING_EXACT", observed_head_binding_exact),
        _check("LATEST_HEAD_QUERY_CLOCK_BINDING_EXACT", query_clock_binding_exact),
        _check("LATEST_HEAD_STORE_BINDING_EXACT", store_binding_exact),
        _check("NEXT_ROLLBACK_CHECKPOINT_EXACT", next_checkpoint_exact),
        _check("V8_EFFECTIVE_BUDGET_PASS", v8_local_pass),
        _check("V8_ADMISSION_AUTHORITY_REMAINS_BLOCKED", v8_authority_locked),
    ]
    local_budget_pass = not _blockers(checks)
    status = "PASS" if local_budget_pass else "BLOCKED"
    document = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "admission_status": "BLOCKED",
        "decision": (
            "PASS_SIGNED_LATEST_HEAD_READ_BOUND_EFFECTIVE_BUDGET_"
            "LATESTNESS_PROVIDER_IDENTITY_AND_DURABILITY_UNVERIFIED"
            if local_budget_pass
            else "BLOCK_LATEST_HEAD_READ_OR_EFFECTIVE_BUDGET_CONTRACT"
        ),
        "source": {
            "latest_head_read_evidence_hash": read_evidence_hash,
            "latest_head_read_claim_hash": _document_sha256(
                read_source.get("latest_head_read_claim_hash")
            ),
            "signed_latest_head_read_hash": _document_sha256(
                read_source.get("signed_latest_head_read_hash")
            ),
            "previous_checkpoint_hash": _document_sha256(
                read_source.get("previous_checkpoint_hash")
            ),
            "next_checkpoint_hash": _document_sha256(
                read_source.get("next_checkpoint_hash")
            ),
            "atomic_store_provider_hash": _document_sha256(
                v8_source.get("atomic_store_provider_hash")
            ),
            "atomic_commit_evidence_hash": _document_sha256(
                v8_source.get("atomic_commit_evidence_hash")
            ),
            "atomic_head_state_hash": _document_sha256(
                v8_source.get("atomic_head_state_hash")
            ),
            "clock_evidence_hash": _document_sha256(
                v8_source.get("clock_evidence_hash")
            ),
            "snapshot_claim_hash": _document_sha256(
                v8_source.get("snapshot_claim_hash")
            ),
            "v8_budget_hash": _document_sha256(v8_document.get("budget_v8_hash")),
        },
        "latest_head_summary": {
            "commit_index": _document_int(read_observation.get("commit_index")),
            "clock_counter": _document_int(read_observation.get("clock_counter")),
            "state_revision": _document_int(read_observation.get("state_revision")),
            "commit_delta_from_floor": _document_int(
                read_observation.get("commit_delta_from_floor")
            ),
        },
        "clock_summary": deepcopy(v8_document.get("clock_summary")),
        "snapshot_summary": deepcopy(v8_document.get("snapshot_summary")),
        "budget_summary": deepcopy(v8_document.get("budget_summary")),
        "checks": checks,
        "facts": {
            "latest_head_read_evidence_exact": read_evidence_exact,
            "preregistered_store_key_read_signature_verified": (
                read_signature_pass
            ),
            "rollback_floor_arithmetic_verified": bool(
                read_facts.get("rollback_floor_arithmetic_verified") is True
            ),
            "latest_head_observation_bound_to_budget": observed_head_binding_exact,
            "latest_head_query_bound_to_signed_clock": query_clock_binding_exact,
            "caller_receipt_without_read_evidence_accepted": False,
            "predecessor_admission_authority_preserved_blocked": (
                v8_authority_locked
            ),
            "latest_atomic_head_verified": False,
            "latest_head_source_truth_verified": False,
            "atomic_store_provider_identity_verified": False,
            "atomic_store_implementation_verified": False,
            "atomic_compare_and_swap_verified": False,
            "atomic_current_head_persistence_verified": False,
            "durability_verified": False,
            "crash_recovery_verified": False,
            "trusted_evaluation_clock_verified": False,
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
    return seal_strict_canonical_document(document, "budget_v9_hash")


def verify_strategy_correlation_cluster_effective_bet_budget_v9(
    document: Any,
    *args: Any,
    expected_budget_v9_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_budget_v9_hash,
            "expected_budget_v9_hash",
        )
        rebuilt = evaluate_strategy_correlation_cluster_effective_bet_budget_v9(
            *args,
            **kwargs,
        )
    except Exception:
        return False
    return (
        rebuilt.get("budget_v9_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )
