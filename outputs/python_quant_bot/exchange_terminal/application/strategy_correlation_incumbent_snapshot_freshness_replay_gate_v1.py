"""Sequence freshness and replay-candidate gate for ADR0378 snapshots.

This pure contract verifies synthetic attestations, a trusted sequence-head
reference, and a caller-supplied replay cursor.  It never persists or advances
the cursor, so it is not an operational anti-replay registry.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1
    as exposure_preflight,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_post_merge_cluster_exposure_gate_v1
    as post_merge_gate,
)


CONTRACT_VERSION: Final = (
    "strategy-correlation-incumbent-snapshot-freshness-replay-gate-v1"
)
ATTESTATION_VERSION: Final = "incumbent-snapshot-sequence-attestation-v1"
REFERENCE_VERSION: Final = "incumbent-snapshot-sequence-head-reference-v1"
CURSOR_VERSION: Final = "incumbent-snapshot-replay-cursor-v1"
POLICY_VERSION: Final = "incumbent-snapshot-freshness-replay-policy-v1"

STATUS_UNKNOWN: Final = "UNKNOWN"
STATUS_BLOCKED_FRESHNESS_OR_REPLAY: Final = (
    "BLOCKED_INCUMBENT_SNAPSHOT_FRESHNESS_OR_REPLAY"
)
STATUS_BLOCKED_UPSTREAM_POST_MERGE: Final = "BLOCKED_UPSTREAM_POST_MERGE_GATE"
STATUS_FRESH_UNREPLAYED_CANDIDATE: Final = (
    "OBSERVED_FRESH_UNREPLAYED_SNAPSHOT_CANDIDATE"
)
PERMISSION_STATE_UNAUTHORIZED: Final = "UNAUTHORIZED"

MAX_CONSUMED_ATTESTATIONS: Final = 64
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")


@dataclass(frozen=True, slots=True)
class IncumbentSnapshotSequenceAttestationV1:
    attestation_version: str
    stream_id: str
    projection_preregistration_hash: str
    incumbent_snapshot_hash: str
    sequence: int
    attestation_hash: str


@dataclass(frozen=True, slots=True)
class IncumbentSnapshotSequenceHeadReferenceV1:
    reference_version: str
    reference_id: str
    stream_id: str
    projection_preregistration_hash: str
    head_sequence: int
    reference_hash: str


@dataclass(frozen=True, slots=True)
class IncumbentSnapshotReplayCursorV1:
    cursor_version: str
    stream_id: str
    projection_preregistration_hash: str
    high_water_sequence: int
    high_water_attestation_hash: str | None
    consumed_attestation_hashes: tuple[str, ...]
    cursor_hash: str


@dataclass(frozen=True, slots=True)
class IncumbentSnapshotFreshnessReplayPolicyV1:
    policy_version: str
    policy_id: str
    max_sequence_lag: int
    max_forward_sequence_jump: int


@dataclass(frozen=True, slots=True)
class IncumbentSnapshotFreshnessReplayResultV1:
    contract_version: str
    status: str
    permission_state: str
    permission: bool
    research_only: bool
    blocker_codes: tuple[str, ...]
    post_merge_result_hash: str
    post_merge_status: str
    attestation_hash: str
    reference_hash: str
    cursor_hash: str
    policy_fingerprint_sha256: str
    snapshot_sequence: int
    head_sequence: int
    sequence_lag: int | None
    cursor_high_water_sequence: int
    cursor_mutation_performed: bool


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _is_plain_int(value: object) -> bool:
    return type(value) is int


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and _OPAQUE_ID_RE.fullmatch(value) is not None


def _digest(value: object) -> str | None:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def _attestation_core(
    *,
    stream_id: str,
    projection_hash: str,
    snapshot_hash: str,
    sequence: int,
) -> dict[str, object]:
    return {
        "attestation_version": ATTESTATION_VERSION,
        "stream_id": stream_id,
        "projection_preregistration_hash": projection_hash,
        "incumbent_snapshot_hash": snapshot_hash,
        "sequence": sequence,
    }


def build_incumbent_snapshot_sequence_attestation_v1(
    *,
    stream_id: Any,
    projection_preregistration_hash: Any,
    incumbent_snapshot_hash: Any,
    sequence: Any,
) -> IncumbentSnapshotSequenceAttestationV1 | None:
    if (
        not _valid_id(stream_id)
        or not _is_hash(projection_preregistration_hash)
        or not _is_hash(incumbent_snapshot_hash)
        or not _is_plain_int(sequence)
        or sequence < 1
    ):
        return None
    core = _attestation_core(
        stream_id=stream_id,
        projection_hash=projection_preregistration_hash,
        snapshot_hash=incumbent_snapshot_hash,
        sequence=sequence,
    )
    attestation_hash = _digest(core)
    if attestation_hash is None:
        return None
    return IncumbentSnapshotSequenceAttestationV1(
        attestation_version=ATTESTATION_VERSION,
        stream_id=stream_id,
        projection_preregistration_hash=projection_preregistration_hash,
        incumbent_snapshot_hash=incumbent_snapshot_hash,
        sequence=sequence,
        attestation_hash=attestation_hash,
    )


def _reference_core(
    *,
    reference_id: str,
    stream_id: str,
    projection_hash: str,
    head_sequence: int,
) -> dict[str, object]:
    return {
        "reference_version": REFERENCE_VERSION,
        "reference_id": reference_id,
        "stream_id": stream_id,
        "projection_preregistration_hash": projection_hash,
        "head_sequence": head_sequence,
    }


def build_incumbent_snapshot_sequence_head_reference_v1(
    *,
    reference_id: Any,
    stream_id: Any,
    projection_preregistration_hash: Any,
    head_sequence: Any,
) -> IncumbentSnapshotSequenceHeadReferenceV1 | None:
    if (
        not _valid_id(reference_id)
        or not _valid_id(stream_id)
        or not _is_hash(projection_preregistration_hash)
        or not _is_plain_int(head_sequence)
        or head_sequence < 0
    ):
        return None
    core = _reference_core(
        reference_id=reference_id,
        stream_id=stream_id,
        projection_hash=projection_preregistration_hash,
        head_sequence=head_sequence,
    )
    reference_hash = _digest(core)
    if reference_hash is None:
        return None
    return IncumbentSnapshotSequenceHeadReferenceV1(
        reference_version=REFERENCE_VERSION,
        reference_id=reference_id,
        stream_id=stream_id,
        projection_preregistration_hash=projection_preregistration_hash,
        head_sequence=head_sequence,
        reference_hash=reference_hash,
    )


def _cursor_core(
    *,
    stream_id: str,
    projection_hash: str,
    high_water_sequence: int,
    high_water_attestation_hash: str | None,
    consumed_attestation_hashes: tuple[str, ...],
) -> dict[str, object]:
    return {
        "cursor_version": CURSOR_VERSION,
        "stream_id": stream_id,
        "projection_preregistration_hash": projection_hash,
        "high_water_sequence": high_water_sequence,
        "high_water_attestation_hash": high_water_attestation_hash,
        "consumed_attestation_hashes": list(consumed_attestation_hashes),
    }


def build_incumbent_snapshot_replay_cursor_v1(
    *,
    stream_id: Any,
    projection_preregistration_hash: Any,
    high_water_sequence: Any,
    high_water_attestation_hash: Any,
    consumed_attestation_hashes: Any,
) -> IncumbentSnapshotReplayCursorV1 | None:
    if (
        not _valid_id(stream_id)
        or not _is_hash(projection_preregistration_hash)
        or not _is_plain_int(high_water_sequence)
        or high_water_sequence < 0
        or type(consumed_attestation_hashes) is not tuple
        or len(consumed_attestation_hashes) > MAX_CONSUMED_ATTESTATIONS
        or any(not _is_hash(value) for value in consumed_attestation_hashes)
        or len(consumed_attestation_hashes)
        != len(set(consumed_attestation_hashes))
        or tuple(sorted(consumed_attestation_hashes))
        != consumed_attestation_hashes
    ):
        return None
    if high_water_sequence == 0:
        if high_water_attestation_hash is not None:
            return None
    elif (
        not _is_hash(high_water_attestation_hash)
        or high_water_attestation_hash not in consumed_attestation_hashes
    ):
        return None
    core = _cursor_core(
        stream_id=stream_id,
        projection_hash=projection_preregistration_hash,
        high_water_sequence=high_water_sequence,
        high_water_attestation_hash=high_water_attestation_hash,
        consumed_attestation_hashes=consumed_attestation_hashes,
    )
    cursor_hash = _digest(core)
    if cursor_hash is None:
        return None
    return IncumbentSnapshotReplayCursorV1(
        cursor_version=CURSOR_VERSION,
        stream_id=stream_id,
        projection_preregistration_hash=projection_preregistration_hash,
        high_water_sequence=high_water_sequence,
        high_water_attestation_hash=high_water_attestation_hash,
        consumed_attestation_hashes=consumed_attestation_hashes,
        cursor_hash=cursor_hash,
    )


def _verify_temporal_objects(
    *,
    attestation: object,
    reference: object,
    cursor: object,
    expected_attestation_hash: object,
    expected_reference_hash: object,
    expected_cursor_hash: object,
    expected_stream_id: object,
    expected_projection_hash: object,
    expected_snapshot_hash: object,
) -> bool:
    if (
        not isinstance(attestation, IncumbentSnapshotSequenceAttestationV1)
        or not isinstance(
            reference,
            IncumbentSnapshotSequenceHeadReferenceV1,
        )
        or not isinstance(cursor, IncumbentSnapshotReplayCursorV1)
        or not _is_hash(expected_attestation_hash)
        or not _is_hash(expected_reference_hash)
        or not _is_hash(expected_cursor_hash)
        or not _valid_id(expected_stream_id)
        or not _is_hash(expected_projection_hash)
        or not _is_hash(expected_snapshot_hash)
        or attestation.attestation_hash != expected_attestation_hash
        or reference.reference_hash != expected_reference_hash
        or cursor.cursor_hash != expected_cursor_hash
        or attestation.stream_id != expected_stream_id
        or reference.stream_id != expected_stream_id
        or cursor.stream_id != expected_stream_id
        or attestation.projection_preregistration_hash
        != expected_projection_hash
        or reference.projection_preregistration_hash
        != expected_projection_hash
        or cursor.projection_preregistration_hash != expected_projection_hash
        or attestation.incumbent_snapshot_hash != expected_snapshot_hash
    ):
        return False
    attestation_expected = _digest(
        _attestation_core(
            stream_id=attestation.stream_id,
            projection_hash=attestation.projection_preregistration_hash,
            snapshot_hash=attestation.incumbent_snapshot_hash,
            sequence=attestation.sequence,
        )
    )
    reference_expected = _digest(
        _reference_core(
            reference_id=reference.reference_id,
            stream_id=reference.stream_id,
            projection_hash=reference.projection_preregistration_hash,
            head_sequence=reference.head_sequence,
        )
    )
    cursor_expected = _digest(
        _cursor_core(
            stream_id=cursor.stream_id,
            projection_hash=cursor.projection_preregistration_hash,
            high_water_sequence=cursor.high_water_sequence,
            high_water_attestation_hash=cursor.high_water_attestation_hash,
            consumed_attestation_hashes=cursor.consumed_attestation_hashes,
        )
    )
    return (
        attestation.attestation_version == ATTESTATION_VERSION
        and reference.reference_version == REFERENCE_VERSION
        and cursor.cursor_version == CURSOR_VERSION
        and attestation_expected == expected_attestation_hash
        and reference_expected == expected_reference_hash
        and cursor_expected == expected_cursor_hash
    )


def _validate_policy(
    policy: object,
) -> tuple[str, ...]:
    if not isinstance(policy, IncumbentSnapshotFreshnessReplayPolicyV1):
        return ("FRESHNESS_REPLAY_POLICY_INVALID",)
    codes: list[str] = []
    if policy.policy_version != POLICY_VERSION:
        codes.append("FRESHNESS_REPLAY_POLICY_VERSION_MISMATCH")
    if not _valid_id(policy.policy_id):
        codes.append("FRESHNESS_REPLAY_POLICY_ID_INVALID")
    if (
        not _is_plain_int(policy.max_sequence_lag)
        or not 0 <= policy.max_sequence_lag <= 64
    ):
        codes.append("MAX_SEQUENCE_LAG_INVALID")
    if (
        not _is_plain_int(policy.max_forward_sequence_jump)
        or not 1 <= policy.max_forward_sequence_jump <= 64
    ):
        codes.append("MAX_FORWARD_SEQUENCE_JUMP_INVALID")
    return tuple(codes)


def _policy_fingerprint(
    policy: IncumbentSnapshotFreshnessReplayPolicyV1,
) -> str | None:
    return _digest(
        {
            "policy_version": policy.policy_version,
            "policy_id": policy.policy_id,
            "max_sequence_lag": policy.max_sequence_lag,
            "max_forward_sequence_jump": policy.max_forward_sequence_jump,
        }
    )


def _post_merge_result_hash(
    result: post_merge_gate.PostMergeClusterExposureResultV1,
) -> str | None:
    return _digest(
        {
            "blocker_codes": list(result.blocker_codes),
            "contract_version": result.contract_version,
            "exposure_policy_fingerprint_sha256": (
                result.exposure_policy_fingerprint_sha256
            ),
            "incumbent_cluster_count": result.incumbent_cluster_count,
            "incumbent_snapshot_hash": result.incumbent_snapshot_hash,
            "incumbent_total_gross_bps": result.incumbent_total_gross_bps,
            "maximum_post_merge_cluster_gross_bps": (
                result.maximum_post_merge_cluster_gross_bps
            ),
            "permission": result.permission,
            "permission_state": result.permission_state,
            "post_merge_cluster_count": result.post_merge_cluster_count,
            "post_merge_total_gross_bps": result.post_merge_total_gross_bps,
            "proposal_count": result.proposal_count,
            "proposed_cluster_count": result.proposed_cluster_count,
            "proposed_total_gross_bps": result.proposed_total_gross_bps,
            "research_only": result.research_only,
            "source_proposal_result_hash": result.source_proposal_result_hash,
            "status": result.status,
        }
    )


def evaluate_incumbent_snapshot_freshness_replay_gate_v1(
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    incumbent_snapshot: post_merge_gate.IncumbentClusterExposureSnapshotV1,
    attestation: IncumbentSnapshotSequenceAttestationV1,
    reference: IncumbentSnapshotSequenceHeadReferenceV1,
    cursor: IncumbentSnapshotReplayCursorV1,
    policy: IncumbentSnapshotFreshnessReplayPolicyV1,
    *,
    expected_incumbent_snapshot_hash: Any,
    expected_attestation_hash: Any,
    expected_reference_hash: Any,
    expected_cursor_hash: Any,
    expected_stream_id: Any,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> IncumbentSnapshotFreshnessReplayResultV1 | None:
    post_merge_result = post_merge_gate.evaluate_post_merge_cluster_exposure_from_verified_batch_v1(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        incumbent_snapshot,
        expected_incumbent_snapshot_hash=expected_incumbent_snapshot_hash,
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    policy_codes = _validate_policy(policy)
    if (
        post_merge_result is None
        or policy_codes
        or not _verify_temporal_objects(
            attestation=attestation,
            reference=reference,
            cursor=cursor,
            expected_attestation_hash=expected_attestation_hash,
            expected_reference_hash=expected_reference_hash,
            expected_cursor_hash=expected_cursor_hash,
            expected_stream_id=expected_stream_id,
            expected_projection_hash=expected_projection_preregistration_hash,
            expected_snapshot_hash=expected_incumbent_snapshot_hash,
        )
    ):
        return None
    policy_hash = _policy_fingerprint(policy)
    post_merge_hash = _post_merge_result_hash(post_merge_result)
    if policy_hash is None or post_merge_hash is None:
        return None

    blocker_codes: list[str] = []
    sequence_lag: int | None = None
    if attestation.sequence > reference.head_sequence:
        blocker_codes.append("SNAPSHOT_SEQUENCE_AHEAD_OF_REFERENCE_HEAD")
        status = STATUS_UNKNOWN
    else:
        sequence_lag = reference.head_sequence - attestation.sequence
        if attestation.attestation_hash in cursor.consumed_attestation_hashes:
            blocker_codes.append("SNAPSHOT_ATTESTATION_ALREADY_CONSUMED")
        if attestation.sequence <= cursor.high_water_sequence:
            blocker_codes.append("SNAPSHOT_SEQUENCE_NOT_ABOVE_HIGH_WATER")
        if (
            attestation.sequence - cursor.high_water_sequence
            > policy.max_forward_sequence_jump
        ):
            blocker_codes.append("SNAPSHOT_SEQUENCE_JUMP_EXCEEDS_POLICY")
        if sequence_lag > policy.max_sequence_lag:
            blocker_codes.append("SNAPSHOT_SEQUENCE_LAG_EXCEEDS_POLICY")
        if blocker_codes:
            status = STATUS_BLOCKED_FRESHNESS_OR_REPLAY
        elif (
            post_merge_result.status
            != post_merge_gate.STATUS_WITHIN_POST_MERGE_LIMIT
        ):
            blocker_codes.append("UPSTREAM_POST_MERGE_GATE_NOT_WITHIN_LIMIT")
            status = STATUS_BLOCKED_UPSTREAM_POST_MERGE
        else:
            status = STATUS_FRESH_UNREPLAYED_CANDIDATE

    return IncumbentSnapshotFreshnessReplayResultV1(
        contract_version=CONTRACT_VERSION,
        status=status,
        permission_state=PERMISSION_STATE_UNAUTHORIZED,
        permission=False,
        research_only=True,
        blocker_codes=tuple(blocker_codes),
        post_merge_result_hash=post_merge_hash,
        post_merge_status=post_merge_result.status,
        attestation_hash=attestation.attestation_hash,
        reference_hash=reference.reference_hash,
        cursor_hash=cursor.cursor_hash,
        policy_fingerprint_sha256=policy_hash,
        snapshot_sequence=attestation.sequence,
        head_sequence=reference.head_sequence,
        sequence_lag=sequence_lag,
        cursor_high_water_sequence=cursor.high_water_sequence,
        cursor_mutation_performed=False,
    )


__all__ = [
    "ATTESTATION_VERSION",
    "CONTRACT_VERSION",
    "CURSOR_VERSION",
    "POLICY_VERSION",
    "REFERENCE_VERSION",
    "STATUS_BLOCKED_FRESHNESS_OR_REPLAY",
    "STATUS_BLOCKED_UPSTREAM_POST_MERGE",
    "STATUS_FRESH_UNREPLAYED_CANDIDATE",
    "STATUS_UNKNOWN",
    "IncumbentSnapshotFreshnessReplayPolicyV1",
    "IncumbentSnapshotFreshnessReplayResultV1",
    "IncumbentSnapshotReplayCursorV1",
    "IncumbentSnapshotSequenceAttestationV1",
    "IncumbentSnapshotSequenceHeadReferenceV1",
    "build_incumbent_snapshot_replay_cursor_v1",
    "build_incumbent_snapshot_sequence_attestation_v1",
    "build_incumbent_snapshot_sequence_head_reference_v1",
    "evaluate_incumbent_snapshot_freshness_replay_gate_v1",
]
