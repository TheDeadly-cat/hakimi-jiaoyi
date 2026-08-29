"""Position-derived post-merge cluster exposure gate for synthetic research.

The v1 post-merge gate accepts an already aggregated incumbent cluster snapshot.
This v2 contract removes the caller's ability to choose those aggregate values:
it derives them from canonical per-symbol gross positions under the exact source
partition, then delegates the limit decision to v1.  It performs no I/O and does
not authenticate the position provider or establish snapshot freshness.
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
    strategy_correlation_history_covered_budget_universe_post_merge_cluster_exposure_gate_v1
    as post_merge_gate,
)


CONTRACT_VERSION: Final = (
    "strategy-correlation-history-covered-budget-universe-position-derived-"
    "post-merge-cluster-exposure-gate-v2"
)
POSITION_SNAPSHOT_CLAIM_VERSION: Final = (
    "incumbent-position-gross-snapshot-claim-v1"
)
PERMISSION_STATE_UNAUTHORIZED: Final = "UNAUTHORIZED"
MAX_POSITIONS: Final = 256

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{0,31}$")


@dataclass(frozen=True, slots=True)
class IncumbentGrossPositionV1:
    symbol: str
    gross_bps: int


@dataclass(frozen=True, slots=True)
class IncumbentPositionGrossSnapshotClaimV1:
    claim_version: str
    snapshot_id: str
    projection_preregistration_hash: str
    positions: tuple[IncumbentGrossPositionV1, ...]
    observed_sequence: int
    position_count: int
    total_gross_bps: int
    positions_fingerprint_sha256: str
    provider_identity_verified: bool
    source_truth_verified: bool
    freshness_verified: bool
    permission: bool
    claim_hash: str


@dataclass(frozen=True, slots=True)
class PositionDerivedPostMergeClusterExposureResultV2:
    contract_version: str
    status: str
    permission_state: str
    permission: bool
    research_only: bool
    blocker_codes: tuple[str, ...]
    source_position_snapshot_claim_hash: str
    positions_fingerprint_sha256: str
    source_position_count: int
    derived_incumbent_snapshot_hash: str
    source_cluster_partition_hash: str
    derivation_hash: str
    source_proposal_result_hash: str
    exposure_policy_fingerprint_sha256: str | None
    proposal_count: int | None
    incumbent_cluster_count: int | None
    proposed_cluster_count: int | None
    post_merge_cluster_count: int | None
    incumbent_total_gross_bps: int | None
    proposed_total_gross_bps: int | None
    post_merge_total_gross_bps: int | None
    maximum_post_merge_cluster_gross_bps: int | None
    provider_identity_verified: bool
    source_truth_verified: bool
    freshness_verified: bool
    cursor_mutation_performed: bool
    result_hash: str


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


def _normalize_positions(
    value: object,
) -> tuple[IncumbentGrossPositionV1, ...] | None:
    if type(value) is not tuple or len(value) > MAX_POSITIONS:
        return None
    normalized: list[IncumbentGrossPositionV1] = []
    seen: set[str] = set()
    for item in value:
        if (
            not isinstance(item, IncumbentGrossPositionV1)
            or not isinstance(item.symbol, str)
            or _SYMBOL_RE.fullmatch(item.symbol) is None
            or item.symbol in seen
            or not _is_plain_int(item.gross_bps)
            or not 1 <= item.gross_bps <= exposure_preflight.MAX_GROSS_BPS
        ):
            return None
        seen.add(item.symbol)
        normalized.append(item)
    canonical = tuple(sorted(normalized, key=lambda item: item.symbol))
    return canonical if value == canonical else None


def _positions_payload(
    positions: tuple[IncumbentGrossPositionV1, ...],
) -> list[dict[str, object]]:
    return [
        {"symbol": item.symbol, "gross_bps": item.gross_bps}
        for item in positions
    ]


def _claim_core(
    *,
    snapshot_id: str,
    projection_preregistration_hash: str,
    positions: tuple[IncumbentGrossPositionV1, ...],
    observed_sequence: int,
    positions_fingerprint_sha256: str,
) -> dict[str, object]:
    return {
        "claim_version": POSITION_SNAPSHOT_CLAIM_VERSION,
        "snapshot_id": snapshot_id,
        "projection_preregistration_hash": projection_preregistration_hash,
        "positions": _positions_payload(positions),
        "observed_sequence": observed_sequence,
        "position_count": len(positions),
        "total_gross_bps": sum(item.gross_bps for item in positions),
        "positions_fingerprint_sha256": positions_fingerprint_sha256,
        "provider_identity_verified": False,
        "source_truth_verified": False,
        "freshness_verified": False,
        "permission": False,
    }


def build_incumbent_position_gross_snapshot_claim_v1(
    *,
    snapshot_id: Any,
    projection_preregistration_hash: Any,
    positions: Any,
    observed_sequence: Any,
) -> IncumbentPositionGrossSnapshotClaimV1 | None:
    if (
        not isinstance(snapshot_id, str)
        or _OPAQUE_ID_RE.fullmatch(snapshot_id) is None
        or not _is_hash(projection_preregistration_hash)
        or not _is_plain_int(observed_sequence)
        or observed_sequence < 1
    ):
        return None
    normalized = _normalize_positions(positions)
    if normalized is None:
        return None
    positions_hash = _canonical_sha256(_positions_payload(normalized))
    if positions_hash is None:
        return None
    core = _claim_core(
        snapshot_id=snapshot_id,
        projection_preregistration_hash=projection_preregistration_hash,
        positions=normalized,
        observed_sequence=observed_sequence,
        positions_fingerprint_sha256=positions_hash,
    )
    claim_hash = _canonical_sha256(core)
    if claim_hash is None:
        return None
    return IncumbentPositionGrossSnapshotClaimV1(
        claim_version=POSITION_SNAPSHOT_CLAIM_VERSION,
        snapshot_id=snapshot_id,
        projection_preregistration_hash=projection_preregistration_hash,
        positions=normalized,
        observed_sequence=observed_sequence,
        position_count=len(normalized),
        total_gross_bps=sum(item.gross_bps for item in normalized),
        positions_fingerprint_sha256=positions_hash,
        provider_identity_verified=False,
        source_truth_verified=False,
        freshness_verified=False,
        permission=False,
        claim_hash=claim_hash,
    )


def _verify_claim(
    claim: object,
    *,
    expected_claim_hash: object,
    expected_projection_hash: object,
) -> bool:
    if (
        not isinstance(claim, IncumbentPositionGrossSnapshotClaimV1)
        or not _is_hash(expected_claim_hash)
        or not _is_hash(expected_projection_hash)
        or claim.claim_version != POSITION_SNAPSHOT_CLAIM_VERSION
        or claim.claim_hash != expected_claim_hash
        or claim.projection_preregistration_hash != expected_projection_hash
        or claim.provider_identity_verified is not False
        or claim.source_truth_verified is not False
        or claim.freshness_verified is not False
        or claim.permission is not False
        or not isinstance(claim.snapshot_id, str)
        or _OPAQUE_ID_RE.fullmatch(claim.snapshot_id) is None
        or not _is_plain_int(claim.observed_sequence)
        or claim.observed_sequence < 1
    ):
        return False
    normalized = _normalize_positions(claim.positions)
    if normalized is None:
        return False
    positions_hash = _canonical_sha256(_positions_payload(normalized))
    if (
        positions_hash is None
        or claim.positions_fingerprint_sha256 != positions_hash
        or claim.position_count != len(normalized)
        or claim.total_gross_bps
        != sum(item.gross_bps for item in normalized)
    ):
        return False
    core = _claim_core(
        snapshot_id=claim.snapshot_id,
        projection_preregistration_hash=claim.projection_preregistration_hash,
        positions=normalized,
        observed_sequence=claim.observed_sequence,
        positions_fingerprint_sha256=positions_hash,
    )
    return _canonical_sha256(core) == expected_claim_hash


def _source_clusters_and_symbol_map(
    projection_verification_context: object,
) -> tuple[list[object], dict[str, str]] | None:
    if not isinstance(projection_verification_context, Mapping):
        return None
    structural = projection_verification_context.get(
        "structural_gate_verification_context"
    )
    if not isinstance(structural, Mapping):
        return None
    budget = structural.get("budget_cluster_preregistration")
    if not isinstance(budget, Mapping):
        return None
    source_clusters = budget.get("expected_clusters")
    if not isinstance(source_clusters, list) or not source_clusters:
        return None
    symbol_map: dict[str, str] = {}
    for cluster in source_clusters:
        if not isinstance(cluster, Mapping) or set(cluster) != {
            "cluster_id",
            "members",
        }:
            return None
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if not isinstance(cluster_id, str) or not isinstance(members, list):
            return None
        for symbol in members:
            if not isinstance(symbol, str) or symbol in symbol_map:
                return None
            symbol_map[symbol] = cluster_id
    return source_clusters, symbol_map


def _derive_snapshot(
    claim: IncumbentPositionGrossSnapshotClaimV1,
    projection_verification_context: object,
) -> post_merge_gate.IncumbentClusterExposureSnapshotV1 | None:
    source = _source_clusters_and_symbol_map(projection_verification_context)
    if source is None:
        return None
    source_clusters, symbol_map = source
    cluster_gross: dict[str, int] = {}
    for position in claim.positions:
        cluster_id = symbol_map.get(position.symbol)
        if cluster_id is None:
            return None
        cluster_gross[cluster_id] = (
            cluster_gross.get(cluster_id, 0) + position.gross_bps
        )
    return post_merge_gate.build_incumbent_cluster_exposure_snapshot_v1(
        snapshot_id=claim.snapshot_id,
        projection_preregistration_hash=(
            claim.projection_preregistration_hash
        ),
        source_clusters=source_clusters,
        cluster_gross_bps=tuple(sorted(cluster_gross.items())),
    )


def _result_core(fields: Mapping[str, object]) -> dict[str, object]:
    return dict(fields)


def build_position_derived_incumbent_cluster_exposure_snapshot_v2(
    position_snapshot_claim: IncumbentPositionGrossSnapshotClaimV1,
    *,
    expected_position_snapshot_claim_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> post_merge_gate.IncumbentClusterExposureSnapshotV1 | None:
    """Build the exact internal v1 snapshot without granting authority."""

    if not _verify_claim(
        position_snapshot_claim,
        expected_claim_hash=expected_position_snapshot_claim_hash,
        expected_projection_hash=expected_projection_preregistration_hash,
    ):
        return None
    return _derive_snapshot(
        position_snapshot_claim,
        projection_verification_context,
    )


def evaluate_position_derived_post_merge_cluster_exposure_from_verified_batch_v2(
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    position_snapshot_claim: IncumbentPositionGrossSnapshotClaimV1,
    *,
    expected_position_snapshot_claim_hash: Any,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> PositionDerivedPostMergeClusterExposureResultV2 | None:
    incumbent_snapshot = build_position_derived_incumbent_cluster_exposure_snapshot_v2(
        position_snapshot_claim,
        expected_position_snapshot_claim_hash=(
            expected_position_snapshot_claim_hash
        ),
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    if incumbent_snapshot is None:
        return None
    downstream = post_merge_gate.evaluate_post_merge_cluster_exposure_from_verified_batch_v1(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        incumbent_snapshot,
        expected_incumbent_snapshot_hash=incumbent_snapshot.snapshot_hash,
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    if downstream is None:
        return None
    derivation_hash = _canonical_sha256(
        {
            "contract_version": CONTRACT_VERSION,
            "source_position_snapshot_claim_hash": (
                position_snapshot_claim.claim_hash
            ),
            "positions_fingerprint_sha256": (
                position_snapshot_claim.positions_fingerprint_sha256
            ),
            "projection_preregistration_hash": (
                expected_projection_preregistration_hash
            ),
            "source_cluster_partition_hash": (
                incumbent_snapshot.source_cluster_partition_hash
            ),
            "derived_incumbent_snapshot_hash": incumbent_snapshot.snapshot_hash,
        }
    )
    if derivation_hash is None:
        return None
    fields: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "status": downstream.status,
        "permission_state": PERMISSION_STATE_UNAUTHORIZED,
        "permission": False,
        "research_only": True,
        "blocker_codes": downstream.blocker_codes,
        "source_position_snapshot_claim_hash": position_snapshot_claim.claim_hash,
        "positions_fingerprint_sha256": (
            position_snapshot_claim.positions_fingerprint_sha256
        ),
        "source_position_count": position_snapshot_claim.position_count,
        "derived_incumbent_snapshot_hash": incumbent_snapshot.snapshot_hash,
        "source_cluster_partition_hash": (
            incumbent_snapshot.source_cluster_partition_hash
        ),
        "derivation_hash": derivation_hash,
        "source_proposal_result_hash": downstream.source_proposal_result_hash,
        "exposure_policy_fingerprint_sha256": (
            downstream.exposure_policy_fingerprint_sha256
        ),
        "proposal_count": downstream.proposal_count,
        "incumbent_cluster_count": downstream.incumbent_cluster_count,
        "proposed_cluster_count": downstream.proposed_cluster_count,
        "post_merge_cluster_count": downstream.post_merge_cluster_count,
        "incumbent_total_gross_bps": downstream.incumbent_total_gross_bps,
        "proposed_total_gross_bps": downstream.proposed_total_gross_bps,
        "post_merge_total_gross_bps": downstream.post_merge_total_gross_bps,
        "maximum_post_merge_cluster_gross_bps": (
            downstream.maximum_post_merge_cluster_gross_bps
        ),
        "provider_identity_verified": False,
        "source_truth_verified": False,
        "freshness_verified": False,
        "cursor_mutation_performed": False,
    }
    result_hash = _canonical_sha256(_result_core(fields))
    if result_hash is None:
        return None
    return PositionDerivedPostMergeClusterExposureResultV2(
        **fields,
        result_hash=result_hash,
    )


def verify_position_derived_post_merge_cluster_exposure_result_v2(
    document: Any,
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    position_snapshot_claim: IncumbentPositionGrossSnapshotClaimV1,
    *,
    expected_position_snapshot_claim_hash: Any,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> bool:
    if not isinstance(
        document,
        PositionDerivedPostMergeClusterExposureResultV2,
    ):
        return False
    expected = evaluate_position_derived_post_merge_cluster_exposure_from_verified_batch_v2(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        position_snapshot_claim,
        expected_position_snapshot_claim_hash=(
            expected_position_snapshot_claim_hash
        ),
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    return expected is not None and document == expected


__all__ = [
    "CONTRACT_VERSION",
    "MAX_POSITIONS",
    "PERMISSION_STATE_UNAUTHORIZED",
    "POSITION_SNAPSHOT_CLAIM_VERSION",
    "IncumbentGrossPositionV1",
    "IncumbentPositionGrossSnapshotClaimV1",
    "PositionDerivedPostMergeClusterExposureResultV2",
    "build_incumbent_position_gross_snapshot_claim_v1",
    "build_position_derived_incumbent_cluster_exposure_snapshot_v2",
    "evaluate_position_derived_post_merge_cluster_exposure_from_verified_batch_v2",
    "verify_position_derived_post_merge_cluster_exposure_result_v2",
]
