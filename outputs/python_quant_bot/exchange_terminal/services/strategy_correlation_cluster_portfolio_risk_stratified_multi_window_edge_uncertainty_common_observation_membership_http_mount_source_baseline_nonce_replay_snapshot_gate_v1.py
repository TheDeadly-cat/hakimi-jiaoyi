"""Fail-closed nonce replay checks over caller-supplied review snapshots.

This module is deliberately pure and unmounted.  It can block a replay that is
present in a supplied snapshot, but it cannot prove that an absent value is new.
Only hashes and bounded control metadata cross this boundary.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


STATIC_FINGERPRINT = "20260823-membership-nonce-replay-snapshot-gate-1"
REVIEW_SCOPE = "source-baseline-signed-review-attestation-v1"

REPLAY_KEY_SCHEMA = (
    "strategy-correlation-cluster-source-baseline-review-replay-key-v1"
)
REPLAY_SNAPSHOT_SCHEMA = (
    "strategy-correlation-cluster-source-baseline-review-replay-snapshot-v1"
)
REPLAY_GATE_RECEIPT_SCHEMA = (
    "strategy-correlation-cluster-source-baseline-review-replay-gate-receipt-v1"
)

_HEX = frozenset("0123456789abcdef")
_REPLAY_KEY_FIELDS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "review_scope",
        "signed_attestation_hash",
        "reviewer_key_sha256",
        "review_nonce_hash",
        "replay_key_hash",
    }
)
_SNAPSHOT_FIELDS = frozenset(
    {
        "schema_version",
        "static_fingerprint",
        "authority",
        "coverage",
        "source_authentication_verified",
        "durable_registry_receipt_verified",
        "linearizable_read_verified",
        "absence_can_authorize",
        "entry_count",
        "entries",
        "replay_snapshot_hash",
    }
)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in _HEX for character in value)
    )


def _require_sha256(name: str, value: Any) -> str:
    if not _is_sha256(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def build_nonce_replay_key_v1(
    *,
    signed_attestation_hash: str,
    reviewer_key_sha256: str,
    review_nonce_hash: str,
) -> dict[str, Any]:
    """Build the bounded replay identity consumed by the snapshot gate."""

    document = {
        "schema_version": REPLAY_KEY_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "review_scope": REVIEW_SCOPE,
        "signed_attestation_hash": _require_sha256(
            "signed_attestation_hash", signed_attestation_hash
        ),
        "reviewer_key_sha256": _require_sha256(
            "reviewer_key_sha256", reviewer_key_sha256
        ),
        "review_nonce_hash": _require_sha256("review_nonce_hash", review_nonce_hash),
    }
    return seal_strict_canonical_document(document, "replay_key_hash")


def _valid_replay_key(value: Any) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != _REPLAY_KEY_FIELDS:
        return False
    try:
        rebuilt = build_nonce_replay_key_v1(
            signed_attestation_hash=value["signed_attestation_hash"],
            reviewer_key_sha256=value["reviewer_key_sha256"],
            review_nonce_hash=value["review_nonce_hash"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(dict(value), rebuilt)


def build_nonce_replay_snapshot_v1(
    *, entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Normalize an unauthenticated, caller-supplied replay snapshot."""

    if isinstance(entries, (str, bytes, bytearray)):
        raise ValueError("entries must be a sequence of replay-key documents")

    normalized: list[dict[str, Any]] = []
    seen_replay_keys: set[str] = set()
    for entry in entries:
        if not _valid_replay_key(entry):
            raise ValueError("entries must contain exact replay-key-v1 documents")
        replay_key_hash = entry["replay_key_hash"]
        if replay_key_hash in seen_replay_keys:
            raise ValueError("entries must not contain duplicate replay keys")
        seen_replay_keys.add(replay_key_hash)
        normalized.append(deepcopy(dict(entry)))

    normalized.sort(key=lambda item: item["replay_key_hash"])
    document = {
        "schema_version": REPLAY_SNAPSHOT_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "authority": "CALLER_SUPPLIED_UNAUTHENTICATED",
        "coverage": "PARTIAL",
        "source_authentication_verified": False,
        "durable_registry_receipt_verified": False,
        "linearizable_read_verified": False,
        "absence_can_authorize": False,
        "entry_count": len(normalized),
        "entries": normalized,
    }
    return seal_strict_canonical_document(document, "replay_snapshot_hash")


def _valid_replay_snapshot(value: Any) -> bool:
    if not isinstance(value, Mapping) or frozenset(value) != _SNAPSHOT_FIELDS:
        return False
    if not isinstance(value.get("entries"), list):
        return False
    try:
        rebuilt = build_nonce_replay_snapshot_v1(entries=value["entries"])
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(dict(value), rebuilt)


def _build_receipt(
    *,
    status: str,
    gate_status: str,
    reason_code: str,
    candidate_replay_key_hash: str | None,
    replay_snapshot_hash: str | None,
    exact_signed_attestation_seen: bool,
    reviewer_nonce_seen: bool,
) -> dict[str, Any]:
    document = {
        "schema_version": REPLAY_GATE_RECEIPT_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "gate_status": gate_status,
        "reason_code": reason_code,
        "candidate_replay_key_hash": candidate_replay_key_hash,
        "replay_snapshot_hash": replay_snapshot_hash,
        "exact_signed_attestation_seen": exact_signed_attestation_seen,
        "reviewer_nonce_seen": reviewer_nonce_seen,
        "snapshot_authority": "CALLER_SUPPLIED_UNAUTHENTICATED",
        "snapshot_coverage": "PARTIAL",
        "source_authentication_verified": False,
        "durable_registry_receipt_verified": False,
        "linearizable_read_verified": False,
        "absence_authorizes_progression": False,
        "http_registered": False,
        "ui_mounted": False,
        "current_activated": False,
        "paper_authorized": False,
        "live_authorized": False,
        "profitability_proven": False,
        "research_only": True,
    }
    return seal_strict_canonical_document(document, "replay_gate_receipt_hash")


def evaluate_nonce_replay_snapshot_gate_v1(
    *,
    candidate_replay_key: Mapping[str, Any],
    replay_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Block observed replays and keep snapshot absence at UNKNOWN.

    The result can never be ``gate_status=PASS`` in v1.  A caller-supplied
    snapshot is useful negative evidence when it contains a duplicate, but its
    absence claim cannot establish novelty or authorize progression.
    """

    if not _valid_replay_key(candidate_replay_key):
        return _build_receipt(
            status="UNKNOWN",
            gate_status="UNKNOWN",
            reason_code="INVALID_CANDIDATE_REPLAY_KEY",
            candidate_replay_key_hash=None,
            replay_snapshot_hash=None,
            exact_signed_attestation_seen=False,
            reviewer_nonce_seen=False,
        )
    if not _valid_replay_snapshot(replay_snapshot):
        return _build_receipt(
            status="UNKNOWN",
            gate_status="UNKNOWN",
            reason_code="INVALID_REPLAY_SNAPSHOT",
            candidate_replay_key_hash=candidate_replay_key["replay_key_hash"],
            replay_snapshot_hash=None,
            exact_signed_attestation_seen=False,
            reviewer_nonce_seen=False,
        )

    exact_signed_attestation_seen = any(
        entry["signed_attestation_hash"]
        == candidate_replay_key["signed_attestation_hash"]
        for entry in replay_snapshot["entries"]
    )
    reviewer_nonce_seen = any(
        entry["reviewer_key_sha256"]
        == candidate_replay_key["reviewer_key_sha256"]
        and entry["review_nonce_hash"]
        == candidate_replay_key["review_nonce_hash"]
        for entry in replay_snapshot["entries"]
    )

    if exact_signed_attestation_seen:
        gate_status = "BLOCK"
        reason_code = "SIGNED_ATTESTATION_REPLAY_OBSERVED"
    elif reviewer_nonce_seen:
        gate_status = "BLOCK"
        reason_code = "REVIEWER_NONCE_REUSE_OBSERVED"
    else:
        gate_status = "UNKNOWN"
        reason_code = "SNAPSHOT_ABSENCE_NOT_AUTHENTICATED_OR_DURABLE"

    return _build_receipt(
        status="PASS",
        gate_status=gate_status,
        reason_code=reason_code,
        candidate_replay_key_hash=candidate_replay_key["replay_key_hash"],
        replay_snapshot_hash=replay_snapshot["replay_snapshot_hash"],
        exact_signed_attestation_seen=exact_signed_attestation_seen,
        reviewer_nonce_seen=reviewer_nonce_seen,
    )
