"""Hash-only read-only projection for ADR0380 synthetic CAS evidence.

The builder reruns the exact ADR0380 simulation and emits only allowlisted
lineage hashes, neutral outcome fields, and explicit non-authority claims. It
does not expose cursor documents, consumed-attestation sets, request nonces, or
raw stream identifiers.
"""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_replay_cursor_cas_transition_v1 as cas,
)


PROJECTION_SCHEMA_VERSION = (
    "strategy-correlation-incumbent-snapshot-replay-cursor-cas-"
    "transition-hash-only-projection-v1"
)
STATIC_FINGERPRINT = (
    "20260824-incumbent-snapshot-replay-cursor-cas-hash-only-"
    "unmounted-permission-lock-1"
)
CONSUMER_STATUS = "UNMOUNTED_READONLY_REPLAY_CURSOR_CAS_CANDIDATE"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_OUTCOMES = frozenset(
    {
        cas.OUTCOME_ALREADY_CONSUMED,
        cas.OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER,
        cas.OUTCOME_COMPARE_AND_SWAP_CONFLICT,
        cas.OUTCOME_ADVANCED_IN_RETURNED_CURSOR,
    }
)
_ALLOWED_GATE_STATUSES = frozenset(
    {cas.GATE_STATUS_BLOCK, cas.GATE_STATUS_UNKNOWN}
)


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _canonical_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return sha256(canonical).hexdigest()


def _stream_id_hash(stream_id: str) -> str:
    return sha256(stream_id.encode("ascii")).hexdigest()


def build_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1(
    base_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    observed_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
    freshness_result: replay_gate.IncumbentSnapshotFreshnessReplayResultV1,
    intent: cas.IncumbentSnapshotReplayCursorCasTransitionIntentV1,
    *,
    expected_intent_hash: Any,
    expected_freshness_result_fingerprint_sha256: Any,
    expected_attestation_hash: Any,
    expected_base_cursor_hash: Any,
    expected_observed_cursor_hash: Any,
    expected_stream_id: Any,
    expected_projection_preregistration_hash: Any,
) -> dict[str, Any] | None:
    simulation = cas.simulate_incumbent_snapshot_replay_cursor_cas_transition_v1(
        base_cursor,
        observed_cursor,
        attestation,
        freshness_result,
        intent,
        expected_intent_hash=expected_intent_hash,
        expected_freshness_result_fingerprint_sha256=(
            expected_freshness_result_fingerprint_sha256
        ),
        expected_attestation_hash=expected_attestation_hash,
        expected_base_cursor_hash=expected_base_cursor_hash,
        expected_observed_cursor_hash=expected_observed_cursor_hash,
        expected_stream_id=expected_stream_id,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
    )
    if simulation is None:
        return None

    receipt = simulation.receipt
    if (
        receipt.outcome not in _ALLOWED_OUTCOMES
        or receipt.gate_status not in _ALLOWED_GATE_STATUSES
        or receipt.permission is not False
        or receipt.research_only is not True
        or receipt.input_cursor_mutation_performed is not False
        or receipt.atomic_storage_commit_verified is not False
        or receipt.durable_commit_verified is not False
        or receipt.linearizable_read_verified is not False
    ):
        return None

    payload: dict[str, Any] = {
        "projection_schema_version": PROJECTION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "source_lineage": {
            "cas_contract_version": simulation.contract_version,
            "intent_hash": receipt.intent_hash,
            "freshness_result_fingerprint_sha256": (
                receipt.freshness_result_fingerprint_sha256
            ),
            "candidate_attestation_hash": receipt.attestation_hash,
            "projection_preregistration_hash": (
                base_cursor.projection_preregistration_hash
            ),
            "stream_id_sha256": _stream_id_hash(base_cursor.stream_id),
            "base_cursor_hash": intent.expected_cursor_hash,
            "observed_cursor_hash": receipt.observed_cursor_hash,
            "returned_cursor_hash": receipt.returned_cursor_hash,
            "transition_receipt_hash": receipt.receipt_hash,
        },
        "observation": {
            "outcome": receipt.outcome,
            "gate_status": receipt.gate_status,
            "candidate_sequence": receipt.candidate_sequence,
            "observed_high_water_sequence": (
                receipt.observed_high_water_sequence
            ),
            "returned_high_water_sequence": (
                receipt.returned_high_water_sequence
            ),
            "returned_cursor_changed": receipt.returned_cursor_changed,
        },
        "authority": {
            "permission_state": "RESEARCH_ONLY",
            "permission": False,
            "paper_authorized": False,
            "live_authorized": False,
            "input_cursor_mutation_performed": False,
            "atomic_storage_commit_verified": False,
            "durable_commit_verified": False,
            "linearizable_read_verified": False,
            "provider_identity_verified": False,
            "current_chain_activated": False,
        },
        "redaction": {
            "raw_stream_id_redacted": True,
            "raw_request_nonce_redacted": True,
            "raw_cursor_documents_redacted": True,
            "raw_consumed_attestation_hashes_redacted": True,
            "raw_high_water_attestation_hash_redacted": True,
            "raw_intent_document_redacted": True,
            "raw_receipt_document_redacted": True,
            "raw_incumbent_snapshot_redacted": True,
            "raw_proposals_and_holdings_redacted": True,
            "raw_signatures_and_keys_redacted": True,
        },
    }
    return {
        **payload,
        "readonly_projection_hash": _canonical_hash(payload),
    }


def verify_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1(
    document: Any,
    base_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    observed_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
    freshness_result: replay_gate.IncumbentSnapshotFreshnessReplayResultV1,
    intent: cas.IncumbentSnapshotReplayCursorCasTransitionIntentV1,
    *,
    expected_readonly_projection_hash: Any,
    expected_intent_hash: Any,
    expected_freshness_result_fingerprint_sha256: Any,
    expected_attestation_hash: Any,
    expected_base_cursor_hash: Any,
    expected_observed_cursor_hash: Any,
    expected_stream_id: Any,
    expected_projection_preregistration_hash: Any,
) -> bool:
    if type(document) is not dict or not _is_sha256(
        expected_readonly_projection_hash
    ):
        return False
    rebuilt = build_incumbent_snapshot_replay_cursor_cas_hash_only_projection_v1(
        base_cursor,
        observed_cursor,
        attestation,
        freshness_result,
        intent,
        expected_intent_hash=expected_intent_hash,
        expected_freshness_result_fingerprint_sha256=(
            expected_freshness_result_fingerprint_sha256
        ),
        expected_attestation_hash=expected_attestation_hash,
        expected_base_cursor_hash=expected_base_cursor_hash,
        expected_observed_cursor_hash=expected_observed_cursor_hash,
        expected_stream_id=expected_stream_id,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
    )
    return (
        rebuilt is not None
        and rebuilt["readonly_projection_hash"]
        == expected_readonly_projection_hash
        and document == rebuilt
    )
