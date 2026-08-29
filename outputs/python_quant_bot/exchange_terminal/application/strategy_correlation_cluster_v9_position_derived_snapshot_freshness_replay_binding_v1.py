"""Bind exact v9-derived incumbent exposure to freshness/replay evidence.

This pure application contract reconstructs the incumbent cluster snapshot from
the exact v9 signed-snapshot adapter claim, verifies the position-derived v2
result, and evaluates the existing freshness/replay gate against that same
snapshot hash and the same signed-snapshot sequence.  It does not persist or
advance a replay cursor and grants no execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final

from exchange_terminal.application import (
    strategy_correlation_cluster_dual_budget_v9_signed_snapshot_position_claim_adapter_v1
    as adapter_contract,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1
    as exposure_preflight,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_position_derived_post_merge_cluster_exposure_gate_v2
    as position_gate,
)
from exchange_terminal.application import (
    strategy_correlation_incumbent_snapshot_freshness_replay_gate_v1
    as freshness_gate,
)


CONTRACT_VERSION: Final = (
    "strategy-correlation-cluster-v9-position-derived-snapshot-"
    "freshness-replay-binding-v1"
)
STATUS_FRESH_UNREPLAYED_BOUND_CANDIDATE: Final = (
    "OBSERVED_V9_POSITION_DERIVED_SNAPSHOT_FRESH_UNREPLAYED_CANDIDATE"
)
STATUS_BLOCKED_BOUND_SNAPSHOT: Final = (
    "BLOCKED_V9_POSITION_DERIVED_SNAPSHOT_FRESHNESS_OR_UPSTREAM"
)
STATUS_UNKNOWN: Final = "UNKNOWN"
PERMISSION_STATE_UNAUTHORIZED: Final = "UNAUTHORIZED"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class V9PositionDerivedSnapshotFreshnessReplayBindingResultV1:
    contract_version: str
    status: str
    permission_state: str
    permission: bool
    research_only: bool
    blocker_codes: tuple[str, ...]
    source_v9_reconciliation_hash: str
    source_adapter_hash: str
    source_position_claim_hash: str
    source_position_derived_result_hash: str
    derived_incumbent_snapshot_hash: str
    source_cluster_partition_hash: str
    position_derived_status: str
    freshness_status: str
    freshness_post_merge_status: str
    freshness_post_merge_result_hash: str
    attestation_hash: str
    reference_hash: str
    cursor_hash: str
    freshness_policy_fingerprint_sha256: str
    snapshot_sequence: int
    head_sequence: int
    sequence_lag: int | None
    cursor_high_water_sequence: int
    v9_adapter_exactly_verified: bool
    position_derived_result_exactly_verified: bool
    snapshot_hash_bound_across_contracts: bool
    snapshot_sequence_bound_across_contracts: bool
    local_sequence_freshness_candidate_observed: bool
    provider_identity_verified: bool
    source_truth_verified: bool
    external_freshness_verified: bool
    replay_registry_persistence_verified: bool
    cursor_mutation_performed: bool
    runtime_consumer_bound: bool
    current_admission_allowed: bool
    paper_authorized: bool
    live_order_allowed: bool
    profitability_proven: bool
    binding_hash: str


def _is_hash(value: object) -> bool:
    return type(value) is str and _HEX64_RE.fullmatch(value) is not None


def _canonical_sha256(value: object) -> str | None:
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


def evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
    adapter_result: adapter_contract.V9SignedSnapshotPositionClaimAdapterResultV1,
    v9_document: Any,
    v9_verification_context: Any,
    position_derived_result: position_gate.PositionDerivedPostMergeClusterExposureResultV2,
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    attestation: freshness_gate.IncumbentSnapshotSequenceAttestationV1,
    reference: freshness_gate.IncumbentSnapshotSequenceHeadReferenceV1,
    cursor: freshness_gate.IncumbentSnapshotReplayCursorV1,
    freshness_policy: freshness_gate.IncumbentSnapshotFreshnessReplayPolicyV1,
    *,
    expected_adapter_hash: Any,
    expected_v9_reconciliation_hash: Any,
    expected_position_derived_result_hash: Any,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
    expected_attestation_hash: Any,
    expected_reference_hash: Any,
    expected_cursor_hash: Any,
    expected_stream_id: Any,
) -> V9PositionDerivedSnapshotFreshnessReplayBindingResultV1 | None:
    if (
        not isinstance(
            adapter_result,
            adapter_contract.V9SignedSnapshotPositionClaimAdapterResultV1,
        )
        or not isinstance(
            position_derived_result,
            position_gate.PositionDerivedPostMergeClusterExposureResultV2,
        )
        or not _is_hash(expected_adapter_hash)
        or adapter_result.adapter_hash != expected_adapter_hash
        or not _is_hash(expected_position_derived_result_hash)
        or position_derived_result.result_hash
        != expected_position_derived_result_hash
        or not adapter_contract.verify_v9_signed_snapshot_position_claim_adapter_v1(
            adapter_result,
            v9_document,
            v9_verification_context,
            expected_v9_reconciliation_hash=expected_v9_reconciliation_hash,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
        )
    ):
        return None

    position_claim = adapter_result.position_claim
    incumbent_snapshot = position_gate.build_position_derived_incumbent_cluster_exposure_snapshot_v2(
        position_claim,
        expected_position_snapshot_claim_hash=position_claim.claim_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    if (
        incumbent_snapshot is None
        or incumbent_snapshot.snapshot_hash
        != position_derived_result.derived_incumbent_snapshot_hash
        or incumbent_snapshot.source_cluster_partition_hash
        != position_derived_result.source_cluster_partition_hash
        or not position_gate.verify_position_derived_post_merge_cluster_exposure_result_v2(
            position_derived_result,
            batch_preflight_document,
            projection_preregistration,
            proposals,
            exposure_policy,
            position_claim,
            expected_position_snapshot_claim_hash=position_claim.claim_hash,
            expected_batch_preflight_hash=expected_batch_preflight_hash,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        )
    ):
        return None

    freshness_result = freshness_gate.evaluate_incumbent_snapshot_freshness_replay_gate_v1(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        incumbent_snapshot,
        attestation,
        reference,
        cursor,
        freshness_policy,
        expected_incumbent_snapshot_hash=incumbent_snapshot.snapshot_hash,
        expected_attestation_hash=expected_attestation_hash,
        expected_reference_hash=expected_reference_hash,
        expected_cursor_hash=expected_cursor_hash,
        expected_stream_id=expected_stream_id,
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    if (
        freshness_result is None
        or freshness_result.snapshot_sequence
        != adapter_result.snapshot_sequence
        or freshness_result.post_merge_status != position_derived_result.status
        or freshness_result.permission is not False
        or freshness_result.cursor_mutation_performed is not False
    ):
        return None

    fresh_candidate = (
        freshness_result.status
        == freshness_gate.STATUS_FRESH_UNREPLAYED_CANDIDATE
    )
    if fresh_candidate:
        status = STATUS_FRESH_UNREPLAYED_BOUND_CANDIDATE
    elif freshness_result.status == freshness_gate.STATUS_UNKNOWN:
        status = STATUS_UNKNOWN
    else:
        status = STATUS_BLOCKED_BOUND_SNAPSHOT
    fields: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "permission_state": PERMISSION_STATE_UNAUTHORIZED,
        "permission": False,
        "research_only": True,
        "blocker_codes": freshness_result.blocker_codes,
        "source_v9_reconciliation_hash": (
            adapter_result.source_v9_reconciliation_hash
        ),
        "source_adapter_hash": adapter_result.adapter_hash,
        "source_position_claim_hash": position_claim.claim_hash,
        "source_position_derived_result_hash": position_derived_result.result_hash,
        "derived_incumbent_snapshot_hash": incumbent_snapshot.snapshot_hash,
        "source_cluster_partition_hash": (
            incumbent_snapshot.source_cluster_partition_hash
        ),
        "position_derived_status": position_derived_result.status,
        "freshness_status": freshness_result.status,
        "freshness_post_merge_status": freshness_result.post_merge_status,
        "freshness_post_merge_result_hash": (
            freshness_result.post_merge_result_hash
        ),
        "attestation_hash": freshness_result.attestation_hash,
        "reference_hash": freshness_result.reference_hash,
        "cursor_hash": freshness_result.cursor_hash,
        "freshness_policy_fingerprint_sha256": (
            freshness_result.policy_fingerprint_sha256
        ),
        "snapshot_sequence": freshness_result.snapshot_sequence,
        "head_sequence": freshness_result.head_sequence,
        "sequence_lag": freshness_result.sequence_lag,
        "cursor_high_water_sequence": (
            freshness_result.cursor_high_water_sequence
        ),
        "v9_adapter_exactly_verified": True,
        "position_derived_result_exactly_verified": True,
        "snapshot_hash_bound_across_contracts": True,
        "snapshot_sequence_bound_across_contracts": True,
        "local_sequence_freshness_candidate_observed": fresh_candidate,
        "provider_identity_verified": False,
        "source_truth_verified": False,
        "external_freshness_verified": False,
        "replay_registry_persistence_verified": False,
        "cursor_mutation_performed": False,
        "runtime_consumer_bound": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "profitability_proven": False,
    }
    binding_hash = _canonical_sha256(fields)
    if binding_hash is None:
        return None
    return V9PositionDerivedSnapshotFreshnessReplayBindingResultV1(
        **fields,
        binding_hash=binding_hash,
    )


def verify_v9_position_derived_snapshot_freshness_replay_binding_v1(
    document: Any,
    adapter_result: adapter_contract.V9SignedSnapshotPositionClaimAdapterResultV1,
    v9_document: Any,
    v9_verification_context: Any,
    position_derived_result: position_gate.PositionDerivedPostMergeClusterExposureResultV2,
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    attestation: freshness_gate.IncumbentSnapshotSequenceAttestationV1,
    reference: freshness_gate.IncumbentSnapshotSequenceHeadReferenceV1,
    cursor: freshness_gate.IncumbentSnapshotReplayCursorV1,
    freshness_policy: freshness_gate.IncumbentSnapshotFreshnessReplayPolicyV1,
    **expected: Any,
) -> bool:
    if not isinstance(
        document,
        V9PositionDerivedSnapshotFreshnessReplayBindingResultV1,
    ):
        return False
    rebuilt = evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1(
        adapter_result,
        v9_document,
        v9_verification_context,
        position_derived_result,
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        attestation,
        reference,
        cursor,
        freshness_policy,
        **expected,
    )
    return rebuilt is not None and document == rebuilt


__all__ = [
    "CONTRACT_VERSION",
    "PERMISSION_STATE_UNAUTHORIZED",
    "STATUS_BLOCKED_BOUND_SNAPSHOT",
    "STATUS_FRESH_UNREPLAYED_BOUND_CANDIDATE",
    "STATUS_UNKNOWN",
    "V9PositionDerivedSnapshotFreshnessReplayBindingResultV1",
    "evaluate_v9_position_derived_snapshot_freshness_replay_binding_v1",
    "verify_v9_position_derived_snapshot_freshness_replay_binding_v1",
]
