from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any

from cryptography.exceptions import InvalidSignature

from . import strategy_correlation_cluster_effective_bet_budget_v10 as budget_v10
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1,
    load_canonical_ed25519_public_key_v1,
)


STATIC_FINGERPRINT = (
    "20260824-witness-anti-replay-ownership-v11-synthetic-lock-1"
)
OWNERSHIP_STATE_SCHEMA_VERSION = (
    "strategy-correlation-witness-anti-replay-ownership-state-v1"
)
OWNERSHIP_CLAIM_SCHEMA_VERSION = (
    "strategy-correlation-witness-anti-replay-ownership-claim-v1"
)
SIGNED_OWNERSHIP_SCHEMA_VERSION = (
    "strategy-correlation-witness-anti-replay-signed-ownership-quorum-v1"
)
OWNERSHIP_EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-witness-anti-replay-ownership-quorum-evidence-v1"
)
BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v11"

_MAX_INTEGER = 9_999_999_999_999_999
_SIGNATURE_DOMAIN = "hakimi.strategy-correlation.witness-anti-replay.v1"
_SIGNATURE_MESSAGE_FORMAT = "RAW_SHA256_DIGEST_BYTES_V1"
_SEQUENCE_ROW_KEYS = {
    "witness_id",
    "sequence",
    "last_attestation_id_hash",
}
_SIGNATURE_ROW_KEYS = {
    "witness_id",
    "public_key_spki_base64",
    "signature_base64",
}
_LIMITATIONS = [
    "WITNESS_OWNERSHIP_STATE_PERSISTENCE_UNVERIFIED",
    "WITNESS_IDENTITIES_AND_IMPLEMENTATIONS_UNVERIFIED",
    "WITNESS_INDEPENDENCE_SOURCE_TRUTH_UNVERIFIED",
    "GLOBAL_LATEST_CHECKPOINT_UNVERIFIED",
    "ATOMIC_STORE_AND_DURABILITY_UNVERIFIED",
    "CLOCK_SNAPSHOT_AND_BROKER_SOURCE_TRUTH_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
]


def _locked_authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "witness_ownership_state_trust_allowed": False,
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


def build_witness_anti_replay_ownership_state_v1(
    witness_set_document: Any,
    *,
    witness_set_build_kwargs: Any,
    ownership_epoch_hash: Any,
    state_revision: Any,
    predecessor_ownership_state_hash: Any,
    last_witness_quorum_evidence_hash: Any,
    witness_sequences: Any,
) -> dict[str, Any]:
    witness_kwargs = _require_mapping(
        witness_set_build_kwargs,
        "witness_set_build_kwargs",
    )
    if not budget_v10.verify_checkpoint_witness_set_preregistration_v1(
        witness_set_document,
        **witness_kwargs,
    ):
        raise ValueError("witness set preregistration is not exact")
    witness_set = _mapping(witness_set_document)
    registered = witness_set.get("witnesses")
    if not isinstance(registered, list):
        raise ValueError("witness set rows are invalid")
    expected_ids = [row.get("witness_id") for row in registered]
    if not isinstance(witness_sequences, list) or len(witness_sequences) != 3:
        raise ValueError("witness_sequences must contain exactly three rows")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(witness_sequences):
        if not isinstance(raw, dict) or set(raw) != _SEQUENCE_ROW_KEYS:
            raise ValueError(f"witness_sequences[{index}] must have exact keys")
        normalized.append(
            {
                "witness_id": _require_identifier(
                    raw["witness_id"],
                    f"witness_sequences[{index}].witness_id",
                ),
                "sequence": _require_int(
                    raw["sequence"],
                    f"witness_sequences[{index}].sequence",
                ),
                "last_attestation_id_hash": _require_sha256(
                    raw["last_attestation_id_hash"],
                    f"witness_sequences[{index}].last_attestation_id_hash",
                ),
            }
        )
    if [row["witness_id"] for row in normalized] != expected_ids:
        raise ValueError("witness sequence rows must exactly match registered order")
    source = _mapping(witness_set.get("source"))
    document = {
        "schema_version": OWNERSHIP_STATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "decision": (
            "LOCAL_WITNESS_ANTI_REPLAY_OWNERSHIP_STATE_CANDIDATE_"
            "PERSISTENCE_IDENTITY_AND_SOURCE_TRUTH_UNVERIFIED"
        ),
        "source": {
            "witness_set_hash": _require_sha256(
                witness_set.get("witness_set_hash"),
                "witness_set_hash",
            ),
            "atomic_store_provider_hash": _require_sha256(
                source.get("atomic_store_provider_hash"),
                "atomic_store_provider_hash",
            ),
            "account_scope_hash": _require_sha256(
                source.get("account_scope_hash"),
                "account_scope_hash",
            ),
            "store_epoch_hash": _require_sha256(
                source.get("store_epoch_hash"),
                "store_epoch_hash",
            ),
            "ownership_epoch_hash": _require_sha256(
                ownership_epoch_hash,
                "ownership_epoch_hash",
            ),
        },
        "state": {
            "state_revision": _require_int(state_revision, "state_revision"),
            "predecessor_ownership_state_hash": _require_sha256(
                predecessor_ownership_state_hash,
                "predecessor_ownership_state_hash",
            ),
            "last_witness_quorum_evidence_hash": _require_sha256(
                last_witness_quorum_evidence_hash,
                "last_witness_quorum_evidence_hash",
            ),
            "witness_sequences": normalized,
        },
        "facts": {
            "local_state_shape_exact": True,
            "witness_set_exact": True,
            "witness_sequence_rows_complete": True,
            "ownership_state_persistence_verified": False,
            "witness_identity_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "ownership_state_hash")


def verify_witness_anti_replay_ownership_state_v1(
    document: Any,
    witness_set_document: Any,
    *,
    expected_ownership_state_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_ownership_state_hash,
            "expected_ownership_state_hash",
        )
        rebuilt = build_witness_anti_replay_ownership_state_v1(
            witness_set_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("ownership_state_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_witness_anti_replay_ownership_claim_v1(
    previous_ownership_state_document: Any,
    witness_set_document: Any,
    *,
    expected_previous_ownership_state_hash: Any,
    previous_ownership_state_build_kwargs: Any,
    attestation_id_hash: Any,
    witness_quorum_evidence_hash: Any,
    previous_checkpoint_hash: Any,
    next_checkpoint_hash: Any,
    commit_index: Any,
    participating_witness_ids: Any,
) -> dict[str, Any]:
    previous_hash = _require_sha256(
        expected_previous_ownership_state_hash,
        "expected_previous_ownership_state_hash",
    )
    previous_kwargs = _require_mapping(
        previous_ownership_state_build_kwargs,
        "previous_ownership_state_build_kwargs",
    )
    if not verify_witness_anti_replay_ownership_state_v1(
        previous_ownership_state_document,
        witness_set_document,
        expected_ownership_state_hash=previous_hash,
        **previous_kwargs,
    ):
        raise ValueError("previous witness ownership state is not exact")
    witness_set = _mapping(witness_set_document)
    registered_ids = [
        row.get("witness_id") for row in witness_set.get("witnesses", [])
    ]
    if (
        not isinstance(participating_witness_ids, list)
        or len(participating_witness_ids) not in (2, 3)
    ):
        raise ValueError("participating_witness_ids must contain two or three IDs")
    participants = [
        _require_identifier(value, "participating_witness_id")
        for value in participating_witness_ids
    ]
    if participants != sorted(participants) or len(set(participants)) != len(
        participants
    ):
        raise ValueError("participating witness IDs must be sorted and unique")
    if any(value not in registered_ids for value in participants):
        raise ValueError("participating witness is not preregistered")

    previous = _mapping(previous_ownership_state_document)
    previous_source = _mapping(previous.get("source"))
    previous_state = _mapping(previous.get("state"))
    previous_revision = _require_int(
        previous_state.get("state_revision"),
        "previous state_revision",
    )
    previous_rows = previous_state.get("witness_sequences")
    if not isinstance(previous_rows, list):
        raise ValueError("previous witness sequence rows are invalid")
    attestation_hash = _require_sha256(
        attestation_id_hash,
        "attestation_id_hash",
    )
    next_rows = []
    sequence_transitions = []
    for row in previous_rows:
        witness_id = row["witness_id"]
        previous_sequence = _require_int(row.get("sequence"), "previous sequence")
        participates = witness_id in participants
        if participates and row.get("last_attestation_id_hash") == attestation_hash:
            raise ValueError("attestation ID must advance for participating witnesses")
        next_sequence = previous_sequence + 1 if participates else previous_sequence
        next_attestation = (
            attestation_hash if participates else row["last_attestation_id_hash"]
        )
        next_rows.append(
            {
                "witness_id": witness_id,
                "sequence": next_sequence,
                "last_attestation_id_hash": next_attestation,
            }
        )
        sequence_transitions.append(
            {
                "witness_id": witness_id,
                "participates": participates,
                "previous_sequence": previous_sequence,
                "next_sequence": next_sequence,
            }
        )
    quorum_hash = _require_sha256(
        witness_quorum_evidence_hash,
        "witness_quorum_evidence_hash",
    )
    next_state = build_witness_anti_replay_ownership_state_v1(
        witness_set_document,
        witness_set_build_kwargs=previous_kwargs["witness_set_build_kwargs"],
        ownership_epoch_hash=previous_source.get("ownership_epoch_hash"),
        state_revision=previous_revision + 1,
        predecessor_ownership_state_hash=previous_hash,
        last_witness_quorum_evidence_hash=quorum_hash,
        witness_sequences=next_rows,
    )
    document = {
        "schema_version": OWNERSHIP_CLAIM_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "BLOCKED",
        "decision": (
            "WITNESS_ANTI_REPLAY_OWNERSHIP_CLAIM_UNSIGNED_"
            "STATE_PERSISTENCE_IDENTITY_AND_SOURCE_TRUTH_UNVERIFIED"
        ),
        "source": {
            "witness_set_hash": _require_sha256(
                previous_source.get("witness_set_hash"),
                "witness_set_hash",
            ),
            "ownership_epoch_hash": _require_sha256(
                previous_source.get("ownership_epoch_hash"),
                "ownership_epoch_hash",
            ),
            "previous_ownership_state_hash": previous_hash,
        },
        "attestation": {
            "attestation_id_hash": attestation_hash,
            "witness_quorum_evidence_hash": quorum_hash,
            "previous_checkpoint_hash": _require_sha256(
                previous_checkpoint_hash,
                "previous_checkpoint_hash",
            ),
            "next_checkpoint_hash": _require_sha256(
                next_checkpoint_hash,
                "next_checkpoint_hash",
            ),
            "commit_index": _require_int(commit_index, "commit_index"),
            "participating_witness_ids": participants,
        },
        "sequence_transitions": sequence_transitions,
        "next_ownership_state_hash": next_state["ownership_state_hash"],
        "next_ownership_state_candidate": next_state,
        "signature_contract": {
            "algorithm": "ED25519",
            "domain": _SIGNATURE_DOMAIN,
            "message_format": _SIGNATURE_MESSAGE_FORMAT,
            "minimum_witness_quorum": 2,
        },
        "facts": {
            "previous_ownership_state_exact": True,
            "participating_sequences_increment_exact": True,
            "nonparticipating_sequences_unchanged": True,
            "attestation_id_advances_for_participants": True,
            "ownership_quorum_signature_verified": False,
            "ownership_state_persistence_verified": False,
            "witness_identity_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "ownership_claim_hash")


def verify_witness_anti_replay_ownership_claim_v1(
    document: Any,
    previous_ownership_state_document: Any,
    witness_set_document: Any,
    *,
    expected_ownership_claim_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_ownership_claim_hash,
            "expected_ownership_claim_hash",
        )
        rebuilt = build_witness_anti_replay_ownership_claim_v1(
            previous_ownership_state_document,
            witness_set_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("ownership_claim_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_signed_witness_anti_replay_ownership_quorum_v1(
    ownership_claim_document: Any,
    previous_ownership_state_document: Any,
    witness_set_document: Any,
    *,
    signature_rows: Any,
    expected_ownership_claim_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_ownership_claim_hash,
        "expected_ownership_claim_hash",
    )
    claim_kwargs = _require_mapping(claim_build_kwargs, "claim_build_kwargs")
    if not verify_witness_anti_replay_ownership_claim_v1(
        ownership_claim_document,
        previous_ownership_state_document,
        witness_set_document,
        expected_ownership_claim_hash=claim_hash,
        **claim_kwargs,
    ):
        raise ValueError("witness ownership claim is not exact")
    claim = _mapping(ownership_claim_document)
    participants = _mapping(claim.get("attestation")).get(
        "participating_witness_ids"
    )
    if not isinstance(signature_rows, list) or not isinstance(participants, list):
        raise ValueError("signature rows and participants must be lists")
    witness_set = _mapping(witness_set_document)
    witness_by_id = {
        row["witness_id"]: row for row in witness_set.get("witnesses", [])
    }
    normalized = []
    for index, raw in enumerate(signature_rows):
        if not isinstance(raw, dict) or set(raw) != _SIGNATURE_ROW_KEYS:
            raise ValueError(f"signature_rows[{index}] must have exact keys")
        witness_id = _require_identifier(raw["witness_id"], "witness_id")
        witness = witness_by_id.get(witness_id)
        if not isinstance(witness, dict):
            raise ValueError("signature witness is not preregistered")
        spki_bytes = decode_canonical_base64_v1(
            raw["public_key_spki_base64"],
            "public_key_spki_base64",
        )
        load_canonical_ed25519_public_key_v1(spki_bytes)
        if hashlib.sha256(spki_bytes).hexdigest() != witness.get(
            "public_key_spki_sha256"
        ):
            raise ValueError("witness public key hash does not match preregistration")
        signature_bytes = decode_canonical_base64_v1(
            raw["signature_base64"],
            "signature_base64",
        )
        if len(signature_bytes) != 64:
            raise ValueError("Ed25519 signature must be 64 bytes")
        normalized.append(deepcopy(raw))
    if [row["witness_id"] for row in normalized] != participants:
        raise ValueError("signature rows must exactly match participating witnesses")
    document = {
        "schema_version": SIGNED_OWNERSHIP_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "ownership_claim_hash": claim_hash,
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
    return seal_strict_canonical_document(document, "signed_ownership_quorum_hash")


def verify_signed_witness_anti_replay_ownership_quorum_v1(
    document: Any,
    ownership_claim_document: Any,
    previous_ownership_state_document: Any,
    witness_set_document: Any,
    *,
    expected_signed_ownership_quorum_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_signed_ownership_quorum_hash,
            "expected_signed_ownership_quorum_hash",
        )
        rebuilt = build_signed_witness_anti_replay_ownership_quorum_v1(
            ownership_claim_document,
            previous_ownership_state_document,
            witness_set_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("signed_ownership_quorum_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_signed_witness_anti_replay_ownership_quorum_v1(
    signed_ownership_quorum_document: Any,
    ownership_claim_document: Any,
    previous_ownership_state_document: Any,
    witness_set_document: Any,
    *,
    signature_rows: Any,
    expected_ownership_claim_hash: Any,
    expected_signed_ownership_quorum_hash: Any,
    claim_build_kwargs: Any,
) -> dict[str, Any]:
    claim_hash = _require_sha256(
        expected_ownership_claim_hash,
        "expected_ownership_claim_hash",
    )
    signed_hash = _require_sha256(
        expected_signed_ownership_quorum_hash,
        "expected_signed_ownership_quorum_hash",
    )
    signed_exact = verify_signed_witness_anti_replay_ownership_quorum_v1(
        signed_ownership_quorum_document,
        ownership_claim_document,
        previous_ownership_state_document,
        witness_set_document,
        expected_signed_ownership_quorum_hash=signed_hash,
        signature_rows=signature_rows,
        expected_ownership_claim_hash=claim_hash,
        claim_build_kwargs=claim_build_kwargs,
    )
    witness_set = _mapping(witness_set_document)
    witness_by_id = {
        row["witness_id"]: row for row in witness_set.get("witnesses", [])
    }
    witness_results = []
    valid_count = 0
    for raw in signature_rows if isinstance(signature_rows, list) else []:
        witness_id = raw.get("witness_id") if isinstance(raw, dict) else None
        witness = witness_by_id.get(witness_id, {})
        signature_verified = False
        signature_hash = None
        try:
            spki_bytes = decode_canonical_base64_v1(
                raw.get("public_key_spki_base64"),
                "public_key_spki_base64",
            )
            signature_bytes = decode_canonical_base64_v1(
                raw.get("signature_base64"),
                "signature_base64",
            )
            signature_hash = hashlib.sha256(signature_bytes).hexdigest()
            public_key = load_canonical_ed25519_public_key_v1(spki_bytes)
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
                "public_key_spki_sha256": witness.get("public_key_spki_sha256"),
                "signature_sha256": signature_hash,
                "status": "PASS" if signature_verified else "BLOCKED",
            }
        )
    quorum_pass = bool(
        signed_exact
        and valid_count >= 2
        and all(row["status"] == "PASS" for row in witness_results)
    )
    checks = [
        _check("SIGNED_OWNERSHIP_QUORUM_EXACT", signed_exact),
        _check("ALL_OWNERSHIP_SIGNATURES_VALID", quorum_pass),
        _check("OWNERSHIP_TWO_OF_THREE_QUORUM_MET", quorum_pass),
    ]
    claim = _mapping(ownership_claim_document)
    document = {
        "schema_version": OWNERSHIP_EVIDENCE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if quorum_pass else "BLOCKED",
        "decision": (
            "WITNESS_OWNERSHIP_SEQUENCE_TRANSITION_KEY_SIGNATURES_OBSERVED_"
            "STATE_PERSISTENCE_IDENTITY_AND_SOURCE_TRUTH_UNVERIFIED"
            if quorum_pass
            else "BLOCK_WITNESS_ANTI_REPLAY_OWNERSHIP_QUORUM_CONTRACT"
        ),
        "source": {
            "witness_set_hash": _document_sha256(
                witness_set.get("witness_set_hash")
            ),
            "ownership_claim_hash": claim_hash,
            "signed_ownership_quorum_hash": signed_hash,
            "previous_ownership_state_hash": _document_sha256(
                _mapping(claim.get("source")).get(
                    "previous_ownership_state_hash"
                )
            ),
            "next_ownership_state_hash": _document_sha256(
                claim.get("next_ownership_state_hash")
            ),
        },
        "attestation": deepcopy(claim.get("attestation")),
        "sequence_transitions": deepcopy(claim.get("sequence_transitions")),
        "quorum_summary": {
            "minimum_witness_quorum": 2,
            "provided_witness_count": len(witness_results),
            "valid_witness_count": valid_count,
        },
        "witness_results": witness_results,
        "checks": checks,
        "facts": {
            "ownership_claim_exact": signed_exact,
            "signed_ownership_quorum_exact": signed_exact,
            "participating_sequences_increment_arithmetic_verified": signed_exact,
            "nonparticipating_sequences_unchanged_arithmetic_verified": signed_exact,
            "two_of_three_ownership_key_signatures_verified": quorum_pass,
            "ownership_state_persistence_verified": False,
            "witness_identities_verified": False,
            "witness_independence_source_truth_verified": False,
            "raw_public_keys_redacted": True,
            "raw_signatures_redacted": True,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "ownership_evidence_hash")


def verify_signed_witness_anti_replay_ownership_evidence_v1(
    document: Any,
    *args: Any,
    expected_ownership_evidence_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_ownership_evidence_hash,
            "expected_ownership_evidence_hash",
        )
        rebuilt = evaluate_signed_witness_anti_replay_ownership_quorum_v1(
            *args,
            **kwargs,
        )
    except Exception:
        return False
    return (
        rebuilt.get("ownership_evidence_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_strategy_correlation_cluster_effective_bet_budget_v11(
    ownership_evidence_document: Any,
    signed_ownership_quorum_document: Any,
    ownership_claim_document: Any,
    previous_ownership_state_document: Any,
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
    expected_ownership_evidence_hash: Any,
    ownership_evaluation_kwargs: Any,
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
    ownership_evidence_hash = _require_sha256(
        expected_ownership_evidence_hash,
        "expected_ownership_evidence_hash",
    )
    ownership_kwargs = _require_mapping(
        ownership_evaluation_kwargs,
        "ownership_evaluation_kwargs",
    )
    ownership_exact = verify_signed_witness_anti_replay_ownership_evidence_v1(
        ownership_evidence_document,
        signed_ownership_quorum_document,
        ownership_claim_document,
        previous_ownership_state_document,
        witness_set_document,
        expected_ownership_evidence_hash=ownership_evidence_hash,
        **ownership_kwargs,
    )
    ownership = _mapping(ownership_evidence_document)
    ownership_facts = _mapping(ownership.get("facts"))
    ownership_source = _mapping(ownership.get("source"))
    ownership_attestation = _mapping(ownership.get("attestation"))
    ownership_pass = bool(
        ownership_exact
        and ownership.get("status") == "PASS"
        and ownership_facts.get(
            "two_of_three_ownership_key_signatures_verified"
        )
        is True
    )
    if ownership_pass:
        try:
            v10_result = (
                budget_v10.evaluate_strategy_correlation_cluster_effective_bet_budget_v10(
                    witness_quorum_evidence_document,
                    signed_witness_quorum_document,
                    witness_quorum_claim_document,
                    witness_set_document,
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
                    expected_witness_quorum_evidence_hash=expected_witness_quorum_evidence_hash,
                    witness_quorum_evaluation_kwargs=witness_quorum_evaluation_kwargs,
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
            v10_result = {}
    else:
        v10_result = {}
    v10_document = _mapping(v10_result)
    v10_source = _mapping(v10_document.get("source"))
    v10_head = _mapping(v10_document.get("latest_head_summary"))
    v10_authority = _mapping(v10_document.get("authority"))
    witness_quorum = _mapping(witness_quorum_evidence_document)
    witness_results = witness_quorum.get("witness_results")
    v10_participants = sorted(
        row.get("witness_id")
        for row in witness_results
        if isinstance(row, dict) and row.get("status") == "PASS"
    ) if isinstance(witness_results, list) else []

    subject_binding_exact = bool(
        ownership_pass
        and ownership_attestation.get("witness_quorum_evidence_hash")
        == v10_source.get("witness_quorum_evidence_hash")
        and ownership_attestation.get("previous_checkpoint_hash")
        == v10_source.get("previous_checkpoint_hash")
        and ownership_attestation.get("next_checkpoint_hash")
        == v10_source.get("next_checkpoint_hash")
        and ownership_attestation.get("commit_index")
        == v10_head.get("commit_index")
    )
    participant_binding_exact = bool(
        ownership_pass
        and ownership_attestation.get("participating_witness_ids")
        == v10_participants
    )
    next_state_exact = bool(
        ownership_pass
        and ownership_source.get("next_ownership_state_hash")
        == _mapping(ownership_claim_document).get("next_ownership_state_hash")
    )
    v10_local_pass = bool(
        v10_document.get("status") == "PASS"
        and v10_document.get("blockers") == []
    )
    v10_authority_locked = bool(
        v10_document.get("admission_status") == "BLOCKED"
        and v10_authority.get("current_admission_allowed") is False
        and v10_authority.get("paper_authorized") is False
        and v10_authority.get("live_order_allowed") is False
    )
    checks = [
        _check("SIGNED_WITNESS_OWNERSHIP_EVIDENCE_EXACT", ownership_exact),
        _check("WITNESS_OWNERSHIP_KEY_SIGNATURES_PASS", ownership_pass),
        _check("OWNERSHIP_TRANSITION_V10_SUBJECT_BINDING_EXACT", subject_binding_exact),
        _check("OWNERSHIP_PARTICIPANTS_MATCH_V10_QUORUM", participant_binding_exact),
        _check("NEXT_OWNERSHIP_STATE_EXACT", next_state_exact),
        _check("V10_EFFECTIVE_BUDGET_PASS", v10_local_pass),
        _check("V10_ADMISSION_AUTHORITY_REMAINS_BLOCKED", v10_authority_locked),
    ]
    local_budget_pass = not _blockers(checks)
    status = "PASS" if local_budget_pass else "BLOCKED"
    document = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "admission_status": "BLOCKED",
        "decision": (
            "PASS_WITNESS_ANTI_REPLAY_OWNERSHIP_BOUND_EFFECTIVE_BUDGET_"
            "STATE_PERSISTENCE_IDENTITY_AND_SOURCE_TRUTH_UNVERIFIED"
            if local_budget_pass
            else "BLOCK_WITNESS_OWNERSHIP_OR_EFFECTIVE_BUDGET_CONTRACT"
        ),
        "source": {
            "witness_set_hash": _document_sha256(v10_source.get("witness_set_hash")),
            "ownership_claim_hash": _document_sha256(
                ownership_source.get("ownership_claim_hash")
            ),
            "signed_ownership_quorum_hash": _document_sha256(
                ownership_source.get("signed_ownership_quorum_hash")
            ),
            "ownership_evidence_hash": ownership_evidence_hash,
            "previous_ownership_state_hash": _document_sha256(
                ownership_source.get("previous_ownership_state_hash")
            ),
            "next_ownership_state_hash": _document_sha256(
                ownership_source.get("next_ownership_state_hash")
            ),
            "witness_quorum_evidence_hash": _document_sha256(
                v10_source.get("witness_quorum_evidence_hash")
            ),
            "next_checkpoint_hash": _document_sha256(
                v10_source.get("next_checkpoint_hash")
            ),
            "v10_budget_hash": _document_sha256(
                v10_document.get("budget_v10_hash")
            ),
        },
        "ownership_summary": {
            "participating_witness_ids": deepcopy(
                ownership_attestation.get("participating_witness_ids")
            ),
            "commit_index": _document_int(
                ownership_attestation.get("commit_index")
            ),
            "sequence_transitions": deepcopy(
                ownership.get("sequence_transitions")
            ),
        },
        "latest_head_summary": deepcopy(v10_document.get("latest_head_summary")),
        "clock_summary": deepcopy(v10_document.get("clock_summary")),
        "snapshot_summary": deepcopy(v10_document.get("snapshot_summary")),
        "budget_summary": deepcopy(v10_document.get("budget_summary")),
        "checks": checks,
        "facts": {
            "ownership_evidence_exact": ownership_exact,
            "participating_witness_sequences_increment_arithmetic_verified": bool(
                ownership_facts.get(
                    "participating_sequences_increment_arithmetic_verified"
                )
                is True
            ),
            "ownership_quorum_bound_to_v10": subject_binding_exact,
            "caller_quorum_without_ownership_transition_accepted": False,
            "predecessor_admission_authority_preserved_blocked": (
                v10_authority_locked
            ),
            "witness_ownership_state_persistence_verified": False,
            "witness_identities_verified": False,
            "witness_independence_source_truth_verified": False,
            "global_latest_checkpoint_verified": False,
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
    return seal_strict_canonical_document(document, "budget_v11_hash")


def verify_strategy_correlation_cluster_effective_bet_budget_v11(
    document: Any,
    *args: Any,
    expected_budget_v11_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_budget_v11_hash,
            "expected_budget_v11_hash",
        )
        rebuilt = evaluate_strategy_correlation_cluster_effective_bet_budget_v11(
            *args,
            **kwargs,
        )
    except Exception:
        return False
    return (
        rebuilt.get("budget_v11_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )
