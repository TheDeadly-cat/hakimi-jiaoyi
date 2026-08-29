"""Pure synthetic post-merge cluster exposure gate.

Proposal-only exposure can pass while the same proposals breach limits after
being combined with incumbent exposure.  This module binds an in-memory
incumbent snapshot to the exact ADR0365 source partition, recomputes ADR0370,
and evaluates post-merge absolute limits.  It has no portfolio reader, runtime,
storage, or trading integration.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final, Mapping

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1
    as exposure_preflight,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_source_receipt_adapter_v1
    as source_adapter,
)


CONTRACT_VERSION: Final = (
    "strategy-correlation-history-covered-budget-universe-"
    "post-merge-cluster-exposure-gate-v1"
)
SNAPSHOT_VERSION: Final = "incumbent-cluster-exposure-snapshot-v1"

STATUS_UNKNOWN: Final = "UNKNOWN"
STATUS_UPSTREAM_PROPOSAL_LIMIT_BREACH: Final = (
    "BLOCKED_UPSTREAM_PROPOSAL_EXPOSURE_LIMIT"
)
STATUS_POST_MERGE_LIMIT_BREACH: Final = (
    "BLOCKED_POST_MERGE_CLUSTER_EXPOSURE_LIMIT"
)
STATUS_WITHIN_POST_MERGE_LIMIT: Final = (
    "OBSERVED_WITHIN_POST_MERGE_PREREGISTERED_EXPOSURE_LIMIT"
)
PERMISSION_STATE_UNAUTHORIZED: Final = "UNAUTHORIZED"

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,31}$")


@dataclass(frozen=True, slots=True)
class IncumbentClusterExposureSnapshotV1:
    snapshot_version: str
    snapshot_id: str
    projection_preregistration_hash: str
    source_cluster_partition_hash: str
    cluster_gross_bps: tuple[tuple[str, int], ...]
    permission: bool
    snapshot_hash: str


@dataclass(frozen=True, slots=True)
class PostMergeClusterExposureResultV1:
    contract_version: str
    status: str
    permission_state: str
    permission: bool
    research_only: bool
    blocker_codes: tuple[str, ...]
    source_proposal_result_hash: str
    incumbent_snapshot_hash: str
    exposure_policy_fingerprint_sha256: str | None
    proposal_count: int | None
    incumbent_cluster_count: int | None
    proposed_cluster_count: int | None
    post_merge_cluster_count: int | None
    incumbent_total_gross_bps: int | None
    proposed_total_gross_bps: int | None
    post_merge_total_gross_bps: int | None
    maximum_post_merge_cluster_gross_bps: int | None


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _is_plain_int(value: object) -> bool:
    return type(value) is int


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


def _normalize_source_clusters(
    source_clusters: object,
) -> tuple[tuple[str, tuple[str, ...]], ...] | None:
    if not isinstance(source_clusters, list) or not source_clusters:
        return None
    normalized: list[tuple[str, tuple[str, ...]]] = []
    seen_cluster_ids: set[str] = set()
    seen_symbols: set[str] = set()
    for cluster in source_clusters:
        if not isinstance(cluster, Mapping) or set(cluster.keys()) != {
            "cluster_id",
            "members",
        }:
            return None
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if (
            not isinstance(cluster_id, str)
            or not _OPAQUE_ID_RE.fullmatch(cluster_id)
            or cluster_id in seen_cluster_ids
            or not isinstance(members, list)
            or not members
            or len(members) != len(set(members))
            or any(
                not isinstance(member, str)
                or not _SYMBOL_RE.fullmatch(member)
                or member in seen_symbols
                for member in members
            )
        ):
            return None
        seen_cluster_ids.add(cluster_id)
        seen_symbols.update(members)
        normalized.append((cluster_id, tuple(members)))
    return tuple(normalized)


def _partition_hash(
    projection_preregistration_hash: str,
    normalized_clusters: tuple[tuple[str, tuple[str, ...]], ...],
) -> str | None:
    return _canonical_sha256(
        {
            "projection_preregistration_hash": projection_preregistration_hash,
            "source_clusters": [
                {"cluster_id": cluster_id, "members": list(members)}
                for cluster_id, members in normalized_clusters
            ],
        }
    )


def _normalize_cluster_gross_bps(
    value: object,
    *,
    allowed_cluster_ids: set[str],
) -> tuple[tuple[str, int], ...] | None:
    if type(value) is not tuple or len(value) > len(allowed_cluster_ids):
        return None
    normalized: list[tuple[str, int]] = []
    seen: set[str] = set()
    for item in value:
        if type(item) is not tuple or len(item) != 2:
            return None
        cluster_id, gross_bps = item
        if (
            not isinstance(cluster_id, str)
            or cluster_id not in allowed_cluster_ids
            or cluster_id in seen
            or not _is_plain_int(gross_bps)
            or not 1 <= gross_bps <= exposure_preflight.MAX_GROSS_BPS
        ):
            return None
        seen.add(cluster_id)
        normalized.append((cluster_id, gross_bps))
    canonical = tuple(sorted(normalized))
    return canonical if tuple(value) == canonical else None


def _snapshot_core(
    *,
    snapshot_id: str,
    projection_preregistration_hash: str,
    source_cluster_partition_hash: str,
    cluster_gross_bps: tuple[tuple[str, int], ...],
) -> dict[str, Any]:
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "snapshot_id": snapshot_id,
        "projection_preregistration_hash": projection_preregistration_hash,
        "source_cluster_partition_hash": source_cluster_partition_hash,
        "cluster_gross_bps": [list(item) for item in cluster_gross_bps],
        "permission": False,
    }


def build_incumbent_cluster_exposure_snapshot_v1(
    *,
    snapshot_id: Any,
    projection_preregistration_hash: Any,
    source_clusters: Any,
    cluster_gross_bps: Any,
) -> IncumbentClusterExposureSnapshotV1 | None:
    if (
        not isinstance(snapshot_id, str)
        or not _OPAQUE_ID_RE.fullmatch(snapshot_id)
        or not _is_hash(projection_preregistration_hash)
    ):
        return None
    normalized_clusters = _normalize_source_clusters(source_clusters)
    if normalized_clusters is None:
        return None
    allowed_cluster_ids = {cluster_id for cluster_id, _ in normalized_clusters}
    normalized_gross = _normalize_cluster_gross_bps(
        cluster_gross_bps,
        allowed_cluster_ids=allowed_cluster_ids,
    )
    if normalized_gross is None:
        return None
    partition_hash = _partition_hash(
        projection_preregistration_hash,
        normalized_clusters,
    )
    if partition_hash is None:
        return None
    core = _snapshot_core(
        snapshot_id=snapshot_id,
        projection_preregistration_hash=projection_preregistration_hash,
        source_cluster_partition_hash=partition_hash,
        cluster_gross_bps=normalized_gross,
    )
    snapshot_hash = _canonical_sha256(core)
    if snapshot_hash is None:
        return None
    return IncumbentClusterExposureSnapshotV1(
        snapshot_version=SNAPSHOT_VERSION,
        snapshot_id=snapshot_id,
        projection_preregistration_hash=projection_preregistration_hash,
        source_cluster_partition_hash=partition_hash,
        cluster_gross_bps=normalized_gross,
        permission=False,
        snapshot_hash=snapshot_hash,
    )


def _source_partition_from_context(
    projection_verification_context: object,
) -> tuple[tuple[str, tuple[str, ...]], ...] | None:
    if not isinstance(projection_verification_context, Mapping):
        return None
    structural_context = projection_verification_context.get(
        "structural_gate_verification_context"
    )
    if not isinstance(structural_context, Mapping):
        return None
    budget = structural_context.get("budget_cluster_preregistration")
    if not isinstance(budget, Mapping):
        return None
    return _normalize_source_clusters(budget.get("expected_clusters"))


def _verify_snapshot(
    snapshot: object,
    *,
    expected_snapshot_hash: object,
    expected_projection_preregistration_hash: object,
    normalized_clusters: tuple[tuple[str, tuple[str, ...]], ...],
) -> bool:
    if (
        not isinstance(snapshot, IncumbentClusterExposureSnapshotV1)
        or not _is_hash(expected_snapshot_hash)
        or not _is_hash(expected_projection_preregistration_hash)
        or snapshot.snapshot_version != SNAPSHOT_VERSION
        or snapshot.snapshot_hash != expected_snapshot_hash
        or snapshot.projection_preregistration_hash
        != expected_projection_preregistration_hash
        or snapshot.permission is not False
        or not isinstance(snapshot.snapshot_id, str)
        or not _OPAQUE_ID_RE.fullmatch(snapshot.snapshot_id)
    ):
        return False
    expected_partition_hash = _partition_hash(
        expected_projection_preregistration_hash,
        normalized_clusters,
    )
    if (
        expected_partition_hash is None
        or snapshot.source_cluster_partition_hash != expected_partition_hash
    ):
        return False
    allowed_ids = {cluster_id for cluster_id, _ in normalized_clusters}
    normalized_gross = _normalize_cluster_gross_bps(
        snapshot.cluster_gross_bps,
        allowed_cluster_ids=allowed_ids,
    )
    if normalized_gross is None:
        return False
    expected_core = _snapshot_core(
        snapshot_id=snapshot.snapshot_id,
        projection_preregistration_hash=snapshot.projection_preregistration_hash,
        source_cluster_partition_hash=snapshot.source_cluster_partition_hash,
        cluster_gross_bps=normalized_gross,
    )
    return _canonical_sha256(expected_core) == expected_snapshot_hash


def _source_result_hash(
    result: exposure_preflight.ClusterExposurePreflightResultV1,
) -> str | None:
    return _canonical_sha256(
        {
            "blocker_codes": list(result.blocker_codes),
            "cluster_gross_bps": [list(item) for item in result.cluster_gross_bps],
            "contract_version": result.contract_version,
            "independent_cluster_count": result.independent_cluster_count,
            "permission": result.permission,
            "permission_state": result.permission_state,
            "policy_fingerprint_sha256": result.policy_fingerprint_sha256,
            "policy_result": result.policy_result,
            "proposal_count": result.proposal_count,
            "research_only": result.research_only,
            "source_batch_fingerprint_sha256": (
                result.source_batch_fingerprint_sha256
            ),
            "total_gross_bps": result.total_gross_bps,
        }
    )


def _no_metrics_result(
    *,
    status: str,
    blocker_codes: tuple[str, ...],
    source_result_hash: str,
    snapshot_hash: str,
    policy_fingerprint: str | None,
) -> PostMergeClusterExposureResultV1:
    return PostMergeClusterExposureResultV1(
        contract_version=CONTRACT_VERSION,
        status=status,
        permission_state=PERMISSION_STATE_UNAUTHORIZED,
        permission=False,
        research_only=True,
        blocker_codes=blocker_codes,
        source_proposal_result_hash=source_result_hash,
        incumbent_snapshot_hash=snapshot_hash,
        exposure_policy_fingerprint_sha256=policy_fingerprint,
        proposal_count=None,
        incumbent_cluster_count=None,
        proposed_cluster_count=None,
        post_merge_cluster_count=None,
        incumbent_total_gross_bps=None,
        proposed_total_gross_bps=None,
        post_merge_total_gross_bps=None,
        maximum_post_merge_cluster_gross_bps=None,
    )


def evaluate_post_merge_cluster_exposure_from_verified_batch_v1(
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    incumbent_snapshot: IncumbentClusterExposureSnapshotV1,
    *,
    expected_incumbent_snapshot_hash: Any,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> PostMergeClusterExposureResultV1 | None:
    source_result = source_adapter.evaluate_cluster_exposure_from_verified_batch_v1(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    normalized_clusters = _source_partition_from_context(
        projection_verification_context
    )
    if (
        source_result is None
        or normalized_clusters is None
        or not _verify_snapshot(
            incumbent_snapshot,
            expected_snapshot_hash=expected_incumbent_snapshot_hash,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            normalized_clusters=normalized_clusters,
        )
    ):
        return None
    result_hash = _source_result_hash(source_result)
    if result_hash is None:
        return None
    if source_result.policy_result == exposure_preflight.POLICY_RESULT_UNKNOWN:
        return _no_metrics_result(
            status=STATUS_UNKNOWN,
            blocker_codes=("UPSTREAM_PROPOSAL_EXPOSURE_CONTRACT_UNKNOWN",),
            source_result_hash=result_hash,
            snapshot_hash=incumbent_snapshot.snapshot_hash,
            policy_fingerprint=source_result.policy_fingerprint_sha256,
        )
    if source_result.policy_result == exposure_preflight.POLICY_RESULT_LIMIT_BREACH:
        return _no_metrics_result(
            status=STATUS_UPSTREAM_PROPOSAL_LIMIT_BREACH,
            blocker_codes=("UPSTREAM_PROPOSAL_EXPOSURE_LIMIT_BREACH",),
            source_result_hash=result_hash,
            snapshot_hash=incumbent_snapshot.snapshot_hash,
            policy_fingerprint=source_result.policy_fingerprint_sha256,
        )

    incumbent_totals = dict(incumbent_snapshot.cluster_gross_bps)
    proposed_totals = dict(source_result.cluster_gross_bps)
    post_merge_totals = dict(incumbent_totals)
    for cluster_id, proposed_gross_bps in proposed_totals.items():
        post_merge_totals[cluster_id] = (
            post_merge_totals.get(cluster_id, 0) + proposed_gross_bps
        )
    incumbent_total = sum(incumbent_totals.values())
    proposed_total = sum(proposed_totals.values())
    post_merge_total = sum(post_merge_totals.values())
    maximum_cluster = max(post_merge_totals.values())

    blocker_codes: list[str] = []
    if maximum_cluster > exposure_policy.max_cluster_gross_bps:
        blocker_codes.append("POST_MERGE_CLUSTER_GROSS_LIMIT_EXCEEDED")
    if post_merge_total > exposure_policy.max_portfolio_gross_bps:
        blocker_codes.append("POST_MERGE_PORTFOLIO_GROSS_LIMIT_EXCEEDED")

    return PostMergeClusterExposureResultV1(
        contract_version=CONTRACT_VERSION,
        status=(
            STATUS_POST_MERGE_LIMIT_BREACH
            if blocker_codes
            else STATUS_WITHIN_POST_MERGE_LIMIT
        ),
        permission_state=PERMISSION_STATE_UNAUTHORIZED,
        permission=False,
        research_only=True,
        blocker_codes=tuple(blocker_codes),
        source_proposal_result_hash=result_hash,
        incumbent_snapshot_hash=incumbent_snapshot.snapshot_hash,
        exposure_policy_fingerprint_sha256=(
            source_result.policy_fingerprint_sha256
        ),
        proposal_count=source_result.proposal_count,
        incumbent_cluster_count=len(incumbent_totals),
        proposed_cluster_count=len(proposed_totals),
        post_merge_cluster_count=len(post_merge_totals),
        incumbent_total_gross_bps=incumbent_total,
        proposed_total_gross_bps=proposed_total,
        post_merge_total_gross_bps=post_merge_total,
        maximum_post_merge_cluster_gross_bps=maximum_cluster,
    )


__all__ = [
    "CONTRACT_VERSION",
    "SNAPSHOT_VERSION",
    "STATUS_POST_MERGE_LIMIT_BREACH",
    "STATUS_UNKNOWN",
    "STATUS_UPSTREAM_PROPOSAL_LIMIT_BREACH",
    "STATUS_WITHIN_POST_MERGE_LIMIT",
    "IncumbentClusterExposureSnapshotV1",
    "PostMergeClusterExposureResultV1",
    "build_incumbent_cluster_exposure_snapshot_v1",
    "evaluate_post_merge_cluster_exposure_from_verified_batch_v1",
]
