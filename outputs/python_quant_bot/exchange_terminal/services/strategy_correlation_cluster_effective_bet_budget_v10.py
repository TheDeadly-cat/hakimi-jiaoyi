from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from cryptography.exceptions import InvalidSignature

from . import strategy_correlation_cluster_effective_bet_budget_v9 as budget_v9
from .strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1 as _decode_canonical_base64,
    load_canonical_ed25519_public_key_v1 as _load_ed25519_public_key,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


STATIC_FINGERPRINT = (
    "20260824-independent-checkpoint-witness-quorum-v10-synthetic-lock-1"
)
WITNESS_SET_SCHEMA_VERSION = (
    "strategy-correlation-checkpoint-witness-set-preregistration-v1"
)
QUORUM_CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-checkpoint-witness-quorum-claim-v1"
)
SIGNED_QUORUM_SCHEMA_VERSION = (
    "strategy-correlation-checkpoint-signed-witness-quorum-v1"
)
QUORUM_EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-checkpoint-witness-quorum-signature-evidence-v1"
)
BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v10"

_MAX_INTEGER = 9_999_999_999_999_999
_SIGNATURE_DOMAIN = "hakimi.strategy-correlation.checkpoint-witness-quorum.v1"
_SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"
_WITNESS_KEYS = {
    "witness_id",
    "key_id",
    "public_key_spki_sha256",
    "trust_domain",
    "failure_domain",
    "implementation_claim_sha256",
}
_SIGNATURE_ROW_KEYS = {
    "witness_id",
    "public_key_spki_base64",
    "signature_base64",
}
_LIMITATIONS = [
    "WITNESS_IDENTITIES_UNVERIFIED",
    "WITNESS_IMPLEMENTATIONS_UNVERIFIED",
    "WITNESS_INDEPENDENCE_SOURCE_TRUTH_UNVERIFIED",
    "GLOBAL_LATEST_CHECKPOINT_UNVERIFIED",
    "ATOMIC_STORE_AND_DURABILITY_UNVERIFIED",
    "CLOCK_SNAPSHOT_AND_BROKER_SOURCE_TRUTH_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
]


def _locked_authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "witness_quorum_trust_allowed": False,
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


def build_checkpoint_witness_set_preregistration_v1(
    *,
    atomic_store_provider_hash: Any,
    account_scope_hash: Any,
    store_epoch_hash: Any,
    minimum_witness_quorum: Any,
    witnesses: Any,
) -> dict[str, Any]:
    quorum = _require_int(minimum_witness_quorum, "minimum_witness_quorum")
    if quorum != 2:
        raise ValueError("minimum witness quorum must be exactly 2")
    if not isinstance(witnesses, list) or len(witnesses) != 3:
        raise ValueError("witnesses must contain exactly three rows")

    normalized: list[dict[str, str]] = []
    for index, raw in enumerate(witnesses):
        if not isinstance(raw, dict) or set(raw) != _WITNESS_KEYS:
            raise ValueError(f"witnesses[{index}] must have exact keys")
        normalized.append(
            {
                "witness_id": _require_identifier(
                    raw["witness_id"],
                    f"witnesses[{index}].witness_id",
                ),
                "key_id": _require_identifier(
                    raw["key_id"],
                    f"witnesses[{index}].key_id",
                ),
                "public_key_spki_sha256": _require_sha256(
                    raw["public_key_spki_sha256"],
                    f"witnesses[{index}].public_key_spki_sha256",
                ),
                "trust_domain": _require_identifier(
                    raw["trust_domain"],
                    f"witnesses[{index}].trust_domain",
                ),
                "failure_domain": _require_identifier(
                    raw["failure_domain"],
                    f"witnesses[{index}].failure_domain",
                ),
                "implementation_claim_sha256": _require_sha256(
                    raw["implementation_claim_sha256"],
                    f"witnesses[{index}].implementation_claim_sha256",
                ),
            }
        )
    if normalized != sorted(normalized, key=lambda row: row["witness_id"]):
        raise ValueError("witnesses must be sorted by witness_id")
    for field in (
        "witness_id",
        "key_id",
        "public_key_spki_sha256",
        "trust_domain",
        "failure_domain",
    ):
        values = [row[field] for row in normalized]
        if len(set(values)) != len(values):
            raise ValueError(f"witness {field} values must be unique")

    document = {
        "schema_version": WITNESS_SET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "THREE_CHECKPOINT_WITNESSES_PREREGISTERED_"
            "IDENTITY_IMPLEMENTATION_AND_INDEPENDENCE_TRUTH_UNVERIFIED"
        ),
        "source": {
            "atomic_store_provider_hash": _require_sha256(
                atomic_store_provider_hash,
                "atomic_store_provider_hash",
            ),
            "account_scope_hash": _require_sha256(
                account_scope_hash,
                "account_scope_hash",
            ),
            "store_epoch_hash": _require_sha256(
                store_epoch_hash,
                "store_epoch_hash",
            ),
        },
        "quorum_policy": {
            "witness_count": 3,
            "minimum_witness_quorum": quorum,
            "maximum_votes_per_failure_domain": 1,
            "maximum_votes_per_trust_domain": 1,
            "all_witness_ids_unique": True,
            "all_key_ids_unique": True,
            "all_failure_domains_unique": True,
            "all_trust_domains_unique": True,
        },
        "witnesses": normalized,
        "facts": {
            "local_preregistration_complete": True,
            "witness_identity_verified": False,
            "witness_implementation_verified": False,
            "witness_failure_domain_independence_verified": False,
            "witness_trust_domain_independence_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "witness_set_hash")


def verify_checkpoint_witness_set_preregistration_v1(
    document: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        rebuilt = build_checkpoint_witness_set_preregistration_v1(**build_kwargs)
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, rebuilt)


def build_checkpoint_witness_quorum_claim_v1(
    witness_set_document: Any,
    *,
    witness_set_build_kwargs: Any,
    attestation_id_hash: Any,
    witness_round: Any,
    previous_checkpoint_hash: Any,
    latest_head_read_evidence_hash: Any,
    next_checkpoint_hash: Any,
    atomic_store_provider_hash: Any,
    atomic_commit_evidence_hash: Any,
    atomic_head_state_hash: Any,
    clock_evidence_hash: Any,
    account_scope_hash: Any,
    commit_index: Any,
    clock_counter: Any,
    state_revision: Any,
    evaluated_at_unix_ms: Any,
) -> dict[str, Any]:
    witness_kwargs = _require_mapping(
        witness_set_build_kwargs,
        "witness_set_build_kwargs",
    )
    if not verify_checkpoint_witness_set_preregistration_v1(
        witness_set_document,
        **witness_kwargs,
    ):
        raise ValueError("witness set preregistration is not exact")
    commit = _require_int(commit_index, "commit_index")
    round_value = _require_int(witness_round, "witness_round")
    if round_value != commit:
        raise ValueError("witness_round must equal commit_index")
    witness_set = _mapping(witness_set_document)
    source = _mapping(witness_set.get("source"))
    document = {
        "schema_version": QUORUM_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "CHECKPOINT_WITNESS_QUORUM_CLAIM_UNSIGNED_"
            "WITNESS_IDENTITY_INDEPENDENCE_AND_GLOBAL_LATESTNESS_UNVERIFIED"
        ),
        "source": {
            "witness_set_hash": _require_sha256(
                witness_set.get("witness_set_hash"),
                "witness_set_hash",
            ),
            "atomic_store_provider_hash": _require_sha256(
                source.get("atomic_store_provider_hash"),
                "witness-set atomic_store_provider_hash",
            ),
            "account_scope_hash": _require_sha256(
                source.get("account_scope_hash"),
                "witness-set account_scope_hash",
            ),
            "store_epoch_hash": _require_sha256(
                source.get("store_epoch_hash"),
                "witness-set store_epoch_hash",
            ),
        },
        "attestation": {
            "attestation_id_hash": _require_sha256(
                attestation_id_hash,
                "attestation_id_hash",
            ),
            "witness_round": round_value,
            "evaluated_at_unix_ms": _require_int(
                evaluated_at_unix_ms,
                "evaluated_at_unix_ms",
            ),
        },
        "subject": {
            "previous_checkpoint_hash": _require_sha256(
                previous_checkpoint_hash,
                "previous_checkpoint_hash",
            ),
            "latest_head_read_evidence_hash": _require_sha256(
                latest_head_read_evidence_hash,
                "latest_head_read_evidence_hash",
            ),
            "next_checkpoint_hash": _require_sha256(
                next_checkpoint_hash,
                "next_checkpoint_hash",
            ),
            "atomic_store_provider_hash": _require_sha256(
                atomic_store_provider_hash,
                "atomic_store_provider_hash",
            ),
            "atomic_commit_evidence_hash": _require_sha256(
                atomic_commit_evidence_hash,
                "atomic_commit_evidence_hash",
            ),
            "atomic_head_state_hash": _require_sha256(
                atomic_head_state_hash,
                "atomic_head_state_hash",
            ),
            "clock_evidence_hash": _require_sha256(
                clock_evidence_hash,
                "clock_evidence_hash",
            ),
            "account_scope_hash": _require_sha256(
                account_scope_hash,
                "account_scope_hash",
            ),
            "commit_index": commit,
            "clock_counter": _require_int(clock_counter, "clock_counter"),
            "state_revision": _require_int(state_revision, "state_revision"),
        },
        "signature_contract": {
            "algorithm": "ED25519",
            "domain": _SIGNATURE_DOMAIN,
            "message_format": _SIGNATURE_MESSAGE_FORMAT,
            "minimum_witness_quorum": 2,
        },
        "facts": {
            "witness_set_exact": True,
            "subject_shape_exact": True,
            "witness_quorum_signature_verified": False,
            "witness_identities_verified": False,
            "witness_independence_source_truth_verified": False,
            "global_latest_checkpoint_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "witness_quorum_claim_hash")


def verify_checkpoint_witness_quorum_claim_v1(
    document: Any,
    witness_set_document: Any,
    *,
    expected_witness_quorum_claim_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_witness_quorum_claim_hash,
            "expected_witness_quorum_claim_hash",
        )
        rebuilt = build_checkpoint_witness_quorum_claim_v1(
            witness_set_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("witness_quorum_claim_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_signed_checkpoint_witness_quorum_v1(
    witness_quorum_claim_document: Any,
    witness_set_document: Any,
    *,
    signature_rows: Any,
    expected_witness_quorum_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_witness_quorum_claim_hash,
        "expected_witness_quorum_claim_hash",
    )
    claim_kwargs = _require_mapping(claim_build_kwargs, "claim_build_kwargs")
    if not verify_checkpoint_witness_quorum_claim_v1(
        witness_quorum_claim_document,
        witness_set_document,
        expected_witness_quorum_claim_hash=claim_hash,
        **claim_kwargs,
    ):
        raise ValueError("witness quorum claim is not exact")
    if not isinstance(signature_rows, list) or not 1 <= len(signature_rows) <= 3:
        raise ValueError("signature_rows must contain one to three rows")
    witness_set = _mapping(witness_set_document)
    witness_by_id = {
        row["witness_id"]: row for row in witness_set.get("witnesses", [])
    }
    normalized: list[dict[str, str]] = []
    for index, raw in enumerate(signature_rows):
        if not isinstance(raw, dict) or set(raw) != _SIGNATURE_ROW_KEYS:
            raise ValueError(f"signature_rows[{index}] must have exact keys")
        witness_id = _require_identifier(
            raw["witness_id"],
            f"signature_rows[{index}].witness_id",
        )
        witness = witness_by_id.get(witness_id)
        if not isinstance(witness, dict):
            raise ValueError("signature witness is not preregistered")
        spki_bytes = _decode_canonical_base64(
            raw["public_key_spki_base64"],
            f"signature_rows[{index}].public_key_spki_base64",
        )
        _load_ed25519_public_key(spki_bytes)
        if hashlib.sha256(spki_bytes).hexdigest() != witness.get(
            "public_key_spki_sha256"
        ):
            raise ValueError("witness public key hash does not match preregistration")
        signature_bytes = _decode_canonical_base64(
            raw["signature_base64"],
            f"signature_rows[{index}].signature_base64",
        )
        if len(signature_bytes) != 64:
            raise ValueError("Ed25519 signature must be 64 bytes")
        normalized.append(
            {
                "witness_id": witness_id,
                "public_key_spki_base64": raw["public_key_spki_base64"],
                "signature_base64": raw["signature_base64"],
            }
        )
    if normalized != sorted(normalized, key=lambda row: row["witness_id"]):
        raise ValueError("signature rows must be sorted by witness_id")
    witness_ids = [row["witness_id"] for row in normalized]
    if len(set(witness_ids)) != len(witness_ids):
        raise ValueError("signature witness IDs must be unique")

    document = {
        "schema_version": SIGNED_QUORUM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "witness_quorum_claim_hash": claim_hash,
        "witness_set_hash": _require_sha256(
            witness_set.get("witness_set_hash"),
            "witness_set_hash",
        ),
        "signature_algorithm": "ED25519",
        "signature_domain": _SIGNATURE_DOMAIN,
        "signature_message_format": _SIGNATURE_MESSAGE_FORMAT,
        "signature_rows": normalized,
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "signed_witness_quorum_hash")


def verify_signed_checkpoint_witness_quorum_v1(
    document: Any,
    witness_quorum_claim_document: Any,
    witness_set_document: Any,
    *,
    expected_signed_witness_quorum_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_signed_witness_quorum_hash,
            "expected_signed_witness_quorum_hash",
        )
        rebuilt = build_signed_checkpoint_witness_quorum_v1(
            witness_quorum_claim_document,
            witness_set_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("signed_witness_quorum_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_signed_checkpoint_witness_quorum_v1(
    signed_witness_quorum_document: Any,
    witness_quorum_claim_document: Any,
    witness_set_document: Any,
    *,
    signature_rows: Any,
    expected_witness_quorum_claim_hash: Any,
    expected_signed_witness_quorum_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_witness_quorum_claim_hash,
        "expected_witness_quorum_claim_hash",
    )
    signed_hash = _require_sha256(
        expected_signed_witness_quorum_hash,
        "expected_signed_witness_quorum_hash",
    )
    signed_exact = verify_signed_checkpoint_witness_quorum_v1(
        signed_witness_quorum_document,
        witness_quorum_claim_document,
        witness_set_document,
        expected_signed_witness_quorum_hash=signed_hash,
        signature_rows=signature_rows,
        expected_witness_quorum_claim_hash=claim_hash,
        claim_build_kwargs=claim_build_kwargs,
    )
    witness_set = _mapping(witness_set_document)
    witness_by_id = {
        row["witness_id"]: row for row in witness_set.get("witnesses", [])
    }
    witness_results: list[dict[str, Any]] = []
    valid_count = 0
    for raw in signature_rows if isinstance(signature_rows, list) else []:
        witness_id = raw.get("witness_id") if isinstance(raw, dict) else None
        witness = witness_by_id.get(witness_id, {})
        signature_verified = False
        signature_hash = None
        try:
            spki_bytes = _decode_canonical_base64(
                raw.get("public_key_spki_base64"),
                "public_key_spki_base64",
            )
            signature_bytes = _decode_canonical_base64(
                raw.get("signature_base64"),
                "signature_base64",
            )
            signature_hash = hashlib.sha256(signature_bytes).hexdigest()
            public_key = _load_ed25519_public_key(spki_bytes)
            if (
                signed_exact
                and hashlib.sha256(spki_bytes).hexdigest()
                == witness.get("public_key_spki_sha256")
            ):
                public_key.verify(signature_bytes, bytes.fromhex(claim_hash))
                signature_verified = True
        except (InvalidSignature, TypeError, ValueError):
            signature_verified = False
        if signature_verified:
            valid_count += 1
        witness_results.append(
            {
                "witness_id": witness_id,
                "trust_domain": witness.get("trust_domain"),
                "failure_domain": witness.get("failure_domain"),
                "public_key_spki_sha256": witness.get("public_key_spki_sha256"),
                "signature_sha256": signature_hash,
                "status": "PASS" if signature_verified else "BLOCKED",
            }
        )
    all_signatures_valid = bool(
        signed_exact
        and witness_results
        and all(row["status"] == "PASS" for row in witness_results)
    )
    quorum_met = bool(all_signatures_valid and valid_count >= 2)
    checks = [
        _check("SIGNED_WITNESS_QUORUM_EXACT", signed_exact),
        _check("ALL_PROVIDED_WITNESS_SIGNATURES_VALID", all_signatures_valid),
        _check("TWO_OF_THREE_WITNESS_QUORUM_MET", quorum_met),
    ]
    claim = _mapping(witness_quorum_claim_document)
    document = {
        "schema_version": QUORUM_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if quorum_met else "BLOCKED",
        "decision": (
            "TWO_OF_THREE_PREREGISTERED_WITNESS_KEY_SIGNATURES_OBSERVED_"
            "IDENTITY_INDEPENDENCE_AND_GLOBAL_LATESTNESS_UNVERIFIED"
            if quorum_met
            else "BLOCK_CHECKPOINT_WITNESS_QUORUM_SIGNATURE_CONTRACT"
        ),
        "source": {
            "witness_set_hash": _document_sha256(
                witness_set.get("witness_set_hash")
            ),
            "witness_quorum_claim_hash": claim_hash,
            "signed_witness_quorum_hash": signed_hash,
            "atomic_store_provider_hash": _document_sha256(
                _mapping(claim.get("source")).get("atomic_store_provider_hash")
            ),
            "account_scope_hash": _document_sha256(
                _mapping(claim.get("source")).get("account_scope_hash")
            ),
            "store_epoch_hash": _document_sha256(
                _mapping(claim.get("source")).get("store_epoch_hash")
            ),
        },
        "attestation": deepcopy(claim.get("attestation")),
        "subject": deepcopy(claim.get("subject")),
        "quorum_summary": {
            "minimum_witness_quorum": 2,
            "provided_witness_count": len(witness_results),
            "valid_witness_count": valid_count,
            "distinct_trust_domain_count": len(
                {row["trust_domain"] for row in witness_results}
            ),
            "distinct_failure_domain_count": len(
                {row["failure_domain"] for row in witness_results}
            ),
        },
        "witness_results": witness_results,
        "checks": checks,
        "facts": {
            "witness_set_exact": signed_exact,
            "signed_witness_quorum_exact": signed_exact,
            "two_of_three_key_signatures_verified": quorum_met,
            "preregistered_failure_domains_distinct": True,
            "preregistered_trust_domains_distinct": True,
            "witness_identities_verified": False,
            "witness_implementations_verified": False,
            "witness_independence_source_truth_verified": False,
            "global_latest_checkpoint_verified": False,
            "raw_public_keys_redacted": True,
            "raw_signatures_redacted": True,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "witness_quorum_evidence_hash")


def verify_signed_checkpoint_witness_quorum_evidence_v1(
    document: Any,
    *args: Any,
    expected_witness_quorum_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_witness_quorum_evidence_hash,
            "expected_witness_quorum_evidence_hash",
        )
        rebuilt = evaluate_signed_checkpoint_witness_quorum_v1(*args, **kwargs)
    except Exception:
        return False
    return (
        rebuilt.get("witness_quorum_evidence_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_strategy_correlation_cluster_effective_bet_budget_v10(
    witness_quorum_evidence_document: Any,
    signed_witness_quorum_document: Any,
    witness_quorum_claim_document: Any,
    witness_set_document: Any,
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
    expected_witness_quorum_evidence_hash: Any,
    witness_quorum_evaluation_kwargs: Any,
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
    quorum_evidence_hash = _require_sha256(
        expected_witness_quorum_evidence_hash,
        "expected_witness_quorum_evidence_hash",
    )
    quorum_kwargs = _require_mapping(
        witness_quorum_evaluation_kwargs,
        "witness_quorum_evaluation_kwargs",
    )
    quorum_exact = verify_signed_checkpoint_witness_quorum_evidence_v1(
        witness_quorum_evidence_document,
        signed_witness_quorum_document,
        witness_quorum_claim_document,
        witness_set_document,
        expected_witness_quorum_evidence_hash=quorum_evidence_hash,
        **quorum_kwargs,
    )
    quorum = _mapping(witness_quorum_evidence_document)
    quorum_facts = _mapping(quorum.get("facts"))
    quorum_source = _mapping(quorum.get("source"))
    quorum_attestation = _mapping(quorum.get("attestation"))
    quorum_subject = _mapping(quorum.get("subject"))
    quorum_summary = _mapping(quorum.get("quorum_summary"))
    quorum_pass = bool(
        quorum_exact
        and quorum.get("status") == "PASS"
        and quorum_facts.get("two_of_three_key_signatures_verified") is True
    )

    if quorum_pass:
        try:
            v9_result = (
                budget_v9.evaluate_strategy_correlation_cluster_effective_bet_budget_v9(
                    latest_head_read_evidence_document,
                    signed_latest_head_read_document,
                    latest_head_read_claim_document,
                    latest_head_checkpoint_document,
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
                    expected_latest_head_read_evidence_hash=expected_latest_head_read_evidence_hash,
                    latest_head_read_evaluation_kwargs=latest_head_read_evaluation_kwargs,
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
            v9_result = {}
    else:
        v9_result = {}
    v9_document = _mapping(v9_result)
    v9_source = _mapping(v9_document.get("source"))
    v9_head = _mapping(v9_document.get("latest_head_summary"))
    v9_clock = _mapping(v9_document.get("clock_summary"))
    v9_authority = _mapping(v9_document.get("authority"))
    atomic_provider = _mapping(atomic_store_provider_document)
    atomic_identity = _mapping(atomic_provider.get("identity"))

    subject_binding_exact = bool(
        quorum_pass
        and quorum_subject.get("previous_checkpoint_hash")
        == v9_source.get("previous_checkpoint_hash")
        and quorum_subject.get("latest_head_read_evidence_hash")
        == v9_source.get("latest_head_read_evidence_hash")
        and quorum_subject.get("next_checkpoint_hash")
        == v9_source.get("next_checkpoint_hash")
        and quorum_subject.get("atomic_store_provider_hash")
        == v9_source.get("atomic_store_provider_hash")
        and quorum_subject.get("atomic_commit_evidence_hash")
        == v9_source.get("atomic_commit_evidence_hash")
        and quorum_subject.get("atomic_head_state_hash")
        == v9_source.get("atomic_head_state_hash")
        and quorum_subject.get("clock_evidence_hash")
        == v9_source.get("clock_evidence_hash")
        and quorum_subject.get("commit_index") == v9_head.get("commit_index")
        and quorum_subject.get("clock_counter") == v9_head.get("clock_counter")
        and quorum_subject.get("state_revision") == v9_head.get("state_revision")
        and quorum_attestation.get("evaluated_at_unix_ms")
        == v9_clock.get("evaluated_at_unix_ms")
        and quorum_attestation.get("witness_round") == v9_head.get("commit_index")
    )
    store_scope_binding_exact = bool(
        quorum_pass
        and quorum_source.get("atomic_store_provider_hash")
        == atomic_provider.get("atomic_store_provider_hash")
        and quorum_source.get("account_scope_hash")
        == quorum_subject.get("account_scope_hash")
        == atomic_identity.get("account_scope_hash")
        and quorum_source.get("store_epoch_hash")
        == atomic_identity.get("store_epoch_hash")
    )
    independent_domains_exact = bool(
        quorum_pass
        and quorum_summary.get("valid_witness_count", 0) >= 2
        and quorum_summary.get("distinct_trust_domain_count", 0)
        == quorum_summary.get("provided_witness_count")
        and quorum_summary.get("distinct_failure_domain_count", 0)
        == quorum_summary.get("provided_witness_count")
    )
    v9_local_pass = bool(
        v9_document.get("status") == "PASS"
        and v9_document.get("blockers") == []
    )
    v9_authority_locked = bool(
        v9_document.get("admission_status") == "BLOCKED"
        and v9_authority.get("current_admission_allowed") is False
        and v9_authority.get("paper_authorized") is False
        and v9_authority.get("live_order_allowed") is False
    )
    checks = [
        _check("SIGNED_WITNESS_QUORUM_EVIDENCE_EXACT", quorum_exact),
        _check("TWO_OF_THREE_WITNESS_KEY_SIGNATURES_PASS", quorum_pass),
        _check("WITNESS_QUORUM_SUBJECT_BINDING_EXACT", subject_binding_exact),
        _check("WITNESS_QUORUM_STORE_SCOPE_BINDING_EXACT", store_scope_binding_exact),
        _check("PREREGISTERED_WITNESS_DOMAINS_DISTINCT", independent_domains_exact),
        _check("V9_EFFECTIVE_BUDGET_PASS", v9_local_pass),
        _check("V9_ADMISSION_AUTHORITY_REMAINS_BLOCKED", v9_authority_locked),
    ]
    local_budget_pass = not _blockers(checks)
    status = "PASS" if local_budget_pass else "BLOCKED"
    document = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "admission_status": "BLOCKED",
        "decision": (
            "PASS_INDEPENDENT_CHECKPOINT_WITNESS_QUORUM_BOUND_EFFECTIVE_BUDGET_"
            "WITNESS_IDENTITY_INDEPENDENCE_AND_GLOBAL_LATESTNESS_UNVERIFIED"
            if local_budget_pass
            else "BLOCK_CHECKPOINT_WITNESS_QUORUM_OR_EFFECTIVE_BUDGET_CONTRACT"
        ),
        "source": {
            "witness_set_hash": _document_sha256(
                quorum_source.get("witness_set_hash")
            ),
            "witness_quorum_claim_hash": _document_sha256(
                quorum_source.get("witness_quorum_claim_hash")
            ),
            "signed_witness_quorum_hash": _document_sha256(
                quorum_source.get("signed_witness_quorum_hash")
            ),
            "witness_quorum_evidence_hash": quorum_evidence_hash,
            "previous_checkpoint_hash": _document_sha256(
                v9_source.get("previous_checkpoint_hash")
            ),
            "next_checkpoint_hash": _document_sha256(
                v9_source.get("next_checkpoint_hash")
            ),
            "latest_head_read_evidence_hash": _document_sha256(
                v9_source.get("latest_head_read_evidence_hash")
            ),
            "atomic_head_state_hash": _document_sha256(
                v9_source.get("atomic_head_state_hash")
            ),
            "clock_evidence_hash": _document_sha256(
                v9_source.get("clock_evidence_hash")
            ),
            "v9_budget_hash": _document_sha256(v9_document.get("budget_v9_hash")),
        },
        "witness_quorum_summary": deepcopy(quorum_summary),
        "latest_head_summary": deepcopy(v9_document.get("latest_head_summary")),
        "clock_summary": deepcopy(v9_document.get("clock_summary")),
        "snapshot_summary": deepcopy(v9_document.get("snapshot_summary")),
        "budget_summary": deepcopy(v9_document.get("budget_summary")),
        "checks": checks,
        "facts": {
            "witness_quorum_evidence_exact": quorum_exact,
            "two_of_three_preregistered_key_signatures_verified": quorum_pass,
            "witness_quorum_bound_to_latest_head_read": subject_binding_exact,
            "preregistered_witness_domains_distinct": independent_domains_exact,
            "caller_checkpoint_without_witness_quorum_accepted": False,
            "predecessor_admission_authority_preserved_blocked": (
                v9_authority_locked
            ),
            "witness_identities_verified": False,
            "witness_implementations_verified": False,
            "witness_independence_source_truth_verified": False,
            "global_latest_checkpoint_verified": False,
            "latest_head_source_truth_verified": False,
            "atomic_compare_and_swap_verified": False,
            "durability_verified": False,
            "trusted_evaluation_clock_verified": False,
            "snapshot_source_truth_verified": False,
            "runtime_gate_integrated": False,
            "execution_verified": False,
            "profitability_proven": False,
            "raw_public_keys_embedded": False,
            "raw_signatures_embedded": False,
            "raw_positions_embedded": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "budget_v10_hash")


def verify_strategy_correlation_cluster_effective_bet_budget_v10(
    document: Any,
    *args: Any,
    expected_budget_v10_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_budget_v10_hash,
            "expected_budget_v10_hash",
        )
        rebuilt = evaluate_strategy_correlation_cluster_effective_bet_budget_v10(
            *args,
            **kwargs,
        )
    except Exception:
        return False
    return (
        rebuilt.get("budget_v10_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )
