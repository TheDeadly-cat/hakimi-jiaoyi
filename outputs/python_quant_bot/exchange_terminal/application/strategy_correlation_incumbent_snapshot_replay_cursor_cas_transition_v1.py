from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any

from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1 as replay_gate,
)


CONTRACT_VERSION = "incumbent-snapshot-replay-cursor-cas-transition-v1"
INTENT_VERSION = "incumbent-snapshot-replay-cursor-cas-intent-v1"
RECEIPT_VERSION = "incumbent-snapshot-replay-cursor-cas-receipt-v1"

OUTCOME_ALREADY_CONSUMED = "ALREADY_CONSUMED"
OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER = (
    "SNAPSHOT_SEQUENCE_NOT_ABOVE_OBSERVED_HIGH_WATER"
)
OUTCOME_COMPARE_AND_SWAP_CONFLICT = "COMPARE_AND_SWAP_CONFLICT"
OUTCOME_ADVANCED_IN_RETURNED_CURSOR = "ADVANCED_IN_RETURNED_CURSOR"

GATE_STATUS_BLOCK = "BLOCK"
GATE_STATUS_UNKNOWN = "UNKNOWN"
PERMISSION_STATE_RESEARCH_ONLY = "RESEARCH_ONLY"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class IncumbentSnapshotReplayCursorCasTransitionIntentV1:
    contract_version: str
    intent_version: str
    stream_id: str
    projection_preregistration_hash: str
    expected_cursor_hash: str
    expected_high_water_sequence: int
    expected_high_water_attestation_hash: str | None
    candidate_attestation_hash: str
    candidate_sequence: int
    freshness_result_fingerprint_sha256: str
    request_nonce_hash: str
    proposed_cursor_hash: str
    intent_hash: str


@dataclass(frozen=True)
class IncumbentSnapshotReplayCursorCasTransitionReceiptV1:
    contract_version: str
    receipt_version: str
    outcome: str
    gate_status: str
    permission_state: str
    permission: bool
    research_only: bool
    intent_hash: str
    freshness_result_fingerprint_sha256: str
    attestation_hash: str
    expected_cursor_hash: str
    observed_cursor_hash: str
    returned_cursor_hash: str
    candidate_sequence: int
    observed_high_water_sequence: int
    returned_high_water_sequence: int
    returned_cursor_changed: bool
    input_cursor_mutation_performed: bool
    atomic_storage_commit_verified: bool
    durable_commit_verified: bool
    linearizable_read_verified: bool
    receipt_hash: str


@dataclass(frozen=True)
class IncumbentSnapshotReplayCursorCasSimulationV1:
    contract_version: str
    receipt: IncumbentSnapshotReplayCursorCasTransitionReceiptV1
    returned_cursor: replay_gate.IncumbentSnapshotReplayCursorV1


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_token(value: Any, *, maximum: int = 160) -> bool:
    if type(value) is not str or not value or value != value.strip():
        return False
    if len(value) > maximum:
        return False
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return sha256(canonical).hexdigest()


def _is_exact_attestation(value: Any) -> bool:
    if type(value) is not replay_gate.IncumbentSnapshotSequenceAttestationV1:
        return False
    rebuilt = replay_gate.build_incumbent_snapshot_sequence_attestation_v1(
        stream_id=value.stream_id,
        projection_preregistration_hash=value.projection_preregistration_hash,
        incumbent_snapshot_hash=value.incumbent_snapshot_hash,
        sequence=value.sequence,
    )
    return rebuilt == value


def _is_exact_cursor(value: Any) -> bool:
    if type(value) is not replay_gate.IncumbentSnapshotReplayCursorV1:
        return False
    rebuilt = replay_gate.build_incumbent_snapshot_replay_cursor_v1(
        stream_id=value.stream_id,
        projection_preregistration_hash=value.projection_preregistration_hash,
        high_water_sequence=value.high_water_sequence,
        high_water_attestation_hash=value.high_water_attestation_hash,
        consumed_attestation_hashes=value.consumed_attestation_hashes,
    )
    return rebuilt == value


def fingerprint_incumbent_snapshot_freshness_replay_result_v1(
    result: Any,
) -> str | None:
    if type(result) is not replay_gate.IncumbentSnapshotFreshnessReplayResultV1:
        return None
    try:
        return _hash_payload(asdict(result))
    except (TypeError, ValueError):
        return None


def _is_bound_candidate_result(
    result: Any,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
    cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    *,
    expected_fingerprint: str,
) -> bool:
    actual_fingerprint = (
        fingerprint_incumbent_snapshot_freshness_replay_result_v1(result)
    )
    if actual_fingerprint != expected_fingerprint:
        return False
    return (
        result.status == replay_gate.STATUS_FRESH_UNREPLAYED_CANDIDATE
        and result.blocker_codes == ()
        and result.permission is False
        and result.research_only is True
        and result.cursor_mutation_performed is False
        and result.attestation_hash == attestation.attestation_hash
        and result.cursor_hash == cursor.cursor_hash
        and result.snapshot_sequence == attestation.sequence
        and result.cursor_high_water_sequence == cursor.high_water_sequence
    )


def _build_proposed_cursor(
    cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
) -> replay_gate.IncumbentSnapshotReplayCursorV1 | None:
    consumed_hashes = tuple(
        sorted(
            set(cursor.consumed_attestation_hashes)
            | {attestation.attestation_hash}
        )
    )
    return replay_gate.build_incumbent_snapshot_replay_cursor_v1(
        stream_id=cursor.stream_id,
        projection_preregistration_hash=cursor.projection_preregistration_hash,
        high_water_sequence=attestation.sequence,
        high_water_attestation_hash=attestation.attestation_hash,
        consumed_attestation_hashes=consumed_hashes,
    )


def build_incumbent_snapshot_replay_cursor_cas_transition_intent_v1(
    freshness_result: replay_gate.IncumbentSnapshotFreshnessReplayResultV1,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
    cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    *,
    request_nonce_hash: Any,
    expected_freshness_result_fingerprint_sha256: Any,
    expected_attestation_hash: Any,
    expected_cursor_hash: Any,
) -> IncumbentSnapshotReplayCursorCasTransitionIntentV1 | None:
    if not _is_exact_attestation(attestation) or not _is_exact_cursor(cursor):
        return None
    if not all(
        _is_sha256(value)
        for value in (
            request_nonce_hash,
            expected_freshness_result_fingerprint_sha256,
            expected_attestation_hash,
            expected_cursor_hash,
        )
    ):
        return None
    if (
        expected_attestation_hash != attestation.attestation_hash
        or expected_cursor_hash != cursor.cursor_hash
        or attestation.stream_id != cursor.stream_id
        or attestation.projection_preregistration_hash
        != cursor.projection_preregistration_hash
    ):
        return None
    if not _is_bound_candidate_result(
        freshness_result,
        attestation,
        cursor,
        expected_fingerprint=expected_freshness_result_fingerprint_sha256,
    ):
        return None

    proposed_cursor = _build_proposed_cursor(cursor, attestation)
    if proposed_cursor is None:
        return None

    payload = {
        "contract_version": CONTRACT_VERSION,
        "intent_version": INTENT_VERSION,
        "stream_id": cursor.stream_id,
        "projection_preregistration_hash": cursor.projection_preregistration_hash,
        "expected_cursor_hash": cursor.cursor_hash,
        "expected_high_water_sequence": cursor.high_water_sequence,
        "expected_high_water_attestation_hash": cursor.high_water_attestation_hash,
        "candidate_attestation_hash": attestation.attestation_hash,
        "candidate_sequence": attestation.sequence,
        "freshness_result_fingerprint_sha256": (
            expected_freshness_result_fingerprint_sha256
        ),
        "request_nonce_hash": request_nonce_hash,
        "proposed_cursor_hash": proposed_cursor.cursor_hash,
    }
    return IncumbentSnapshotReplayCursorCasTransitionIntentV1(
        **payload,
        intent_hash=_hash_payload(payload),
    )


def _build_receipt(
    *,
    intent: IncumbentSnapshotReplayCursorCasTransitionIntentV1,
    observed_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    returned_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    outcome: str,
    gate_status: str,
    returned_cursor_changed: bool,
) -> IncumbentSnapshotReplayCursorCasTransitionReceiptV1:
    payload = {
        "contract_version": CONTRACT_VERSION,
        "receipt_version": RECEIPT_VERSION,
        "outcome": outcome,
        "gate_status": gate_status,
        "permission_state": PERMISSION_STATE_RESEARCH_ONLY,
        "permission": False,
        "research_only": True,
        "intent_hash": intent.intent_hash,
        "freshness_result_fingerprint_sha256": (
            intent.freshness_result_fingerprint_sha256
        ),
        "attestation_hash": intent.candidate_attestation_hash,
        "expected_cursor_hash": intent.expected_cursor_hash,
        "observed_cursor_hash": observed_cursor.cursor_hash,
        "returned_cursor_hash": returned_cursor.cursor_hash,
        "candidate_sequence": intent.candidate_sequence,
        "observed_high_water_sequence": observed_cursor.high_water_sequence,
        "returned_high_water_sequence": returned_cursor.high_water_sequence,
        "returned_cursor_changed": returned_cursor_changed,
        "input_cursor_mutation_performed": False,
        "atomic_storage_commit_verified": False,
        "durable_commit_verified": False,
        "linearizable_read_verified": False,
    }
    return IncumbentSnapshotReplayCursorCasTransitionReceiptV1(
        **payload,
        receipt_hash=_hash_payload(payload),
    )


def simulate_incumbent_snapshot_replay_cursor_cas_transition_v1(
    base_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    observed_cursor: replay_gate.IncumbentSnapshotReplayCursorV1,
    attestation: replay_gate.IncumbentSnapshotSequenceAttestationV1,
    freshness_result: replay_gate.IncumbentSnapshotFreshnessReplayResultV1,
    intent: IncumbentSnapshotReplayCursorCasTransitionIntentV1,
    *,
    expected_intent_hash: Any,
    expected_freshness_result_fingerprint_sha256: Any,
    expected_attestation_hash: Any,
    expected_base_cursor_hash: Any,
    expected_observed_cursor_hash: Any,
    expected_stream_id: Any,
    expected_projection_preregistration_hash: Any,
) -> IncumbentSnapshotReplayCursorCasSimulationV1 | None:
    if not _is_exact_cursor(base_cursor) or not _is_exact_cursor(observed_cursor):
        return None
    if not _is_exact_attestation(attestation):
        return None
    if type(intent) is not IncumbentSnapshotReplayCursorCasTransitionIntentV1:
        return None
    if not _is_token(expected_stream_id):
        return None
    if not all(
        _is_sha256(value)
        for value in (
            expected_intent_hash,
            expected_freshness_result_fingerprint_sha256,
            expected_attestation_hash,
            expected_base_cursor_hash,
            expected_observed_cursor_hash,
            expected_projection_preregistration_hash,
        )
    ):
        return None
    if (
        expected_intent_hash != intent.intent_hash
        or expected_freshness_result_fingerprint_sha256
        != intent.freshness_result_fingerprint_sha256
        or expected_attestation_hash != attestation.attestation_hash
        or expected_base_cursor_hash != base_cursor.cursor_hash
        or expected_observed_cursor_hash != observed_cursor.cursor_hash
        or expected_stream_id != base_cursor.stream_id
        or expected_stream_id != observed_cursor.stream_id
        or expected_stream_id != attestation.stream_id
        or expected_projection_preregistration_hash
        != base_cursor.projection_preregistration_hash
        or expected_projection_preregistration_hash
        != observed_cursor.projection_preregistration_hash
        or expected_projection_preregistration_hash
        != attestation.projection_preregistration_hash
    ):
        return None

    rebuilt_intent = (
        build_incumbent_snapshot_replay_cursor_cas_transition_intent_v1(
            freshness_result,
            attestation,
            base_cursor,
            request_nonce_hash=intent.request_nonce_hash,
            expected_freshness_result_fingerprint_sha256=(
                expected_freshness_result_fingerprint_sha256
            ),
            expected_attestation_hash=expected_attestation_hash,
            expected_cursor_hash=expected_base_cursor_hash,
        )
    )
    if rebuilt_intent != intent:
        return None
    if (
        observed_cursor.cursor_hash == intent.expected_cursor_hash
        and observed_cursor != base_cursor
    ):
        return None

    if attestation.attestation_hash in observed_cursor.consumed_attestation_hashes:
        returned_cursor = observed_cursor
        outcome = OUTCOME_ALREADY_CONSUMED
        gate_status = GATE_STATUS_BLOCK
        returned_cursor_changed = False
    elif attestation.sequence <= observed_cursor.high_water_sequence:
        returned_cursor = observed_cursor
        outcome = OUTCOME_SEQUENCE_NOT_ABOVE_HIGH_WATER
        gate_status = GATE_STATUS_BLOCK
        returned_cursor_changed = False
    elif observed_cursor.cursor_hash != intent.expected_cursor_hash:
        returned_cursor = observed_cursor
        outcome = OUTCOME_COMPARE_AND_SWAP_CONFLICT
        gate_status = GATE_STATUS_UNKNOWN
        returned_cursor_changed = False
    else:
        proposed_cursor = _build_proposed_cursor(observed_cursor, attestation)
        if (
            proposed_cursor is None
            or proposed_cursor.cursor_hash != intent.proposed_cursor_hash
        ):
            return None
        returned_cursor = proposed_cursor
        outcome = OUTCOME_ADVANCED_IN_RETURNED_CURSOR
        gate_status = GATE_STATUS_UNKNOWN
        returned_cursor_changed = True

    receipt = _build_receipt(
        intent=intent,
        observed_cursor=observed_cursor,
        returned_cursor=returned_cursor,
        outcome=outcome,
        gate_status=gate_status,
        returned_cursor_changed=returned_cursor_changed,
    )
    return IncumbentSnapshotReplayCursorCasSimulationV1(
        contract_version=CONTRACT_VERSION,
        receipt=receipt,
        returned_cursor=returned_cursor,
    )
