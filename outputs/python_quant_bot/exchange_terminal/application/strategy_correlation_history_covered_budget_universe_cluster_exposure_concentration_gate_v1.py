"""Research-only cluster exposure concentration gate.

Absolute proposal, cluster, and portfolio limits do not prove that exposure is
well distributed across independent source clusters.  This additive gate
recomputes the exact ADR0370 path and applies preregistered integer concentration
limits without exposing raw cluster ids or granting authority.
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
    strategy_correlation_history_covered_budget_universe_cluster_exposure_source_receipt_adapter_v1
    as source_adapter,
)


CONTRACT_VERSION: Final = (
    "strategy-correlation-history-covered-budget-universe-"
    "cluster-exposure-concentration-gate-v1"
)
POLICY_VERSION: Final = "correlation-cluster-exposure-concentration-policy-v1"

STATUS_UNKNOWN: Final = "UNKNOWN"
STATUS_UPSTREAM_LIMIT_BREACH: Final = "BLOCKED_UPSTREAM_EXPOSURE_LIMIT"
STATUS_CONCENTRATION_LIMIT_BREACH: Final = (
    "BLOCKED_PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT"
)
STATUS_WITHIN_CONCENTRATION_LIMIT: Final = (
    "OBSERVED_WITHIN_PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT"
)
PERMISSION_STATE_UNAUTHORIZED: Final = "UNAUTHORIZED"

SHARE_SCALE_BPS: Final = 10_000
HHI_SCALE_PPM: Final = 1_000_000
EFFECTIVE_CLUSTER_SCALE_MILLI: Final = 1_000

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")
_POLICY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")


@dataclass(frozen=True, slots=True)
class ClusterExposureConcentrationPolicyV1:
    policy_version: str
    policy_id: str
    min_independent_clusters: int
    max_largest_cluster_share_bps: int
    max_hhi_ppm: int


@dataclass(frozen=True, slots=True)
class ClusterExposureConcentrationResultV1:
    contract_version: str
    status: str
    permission_state: str
    permission: bool
    research_only: bool
    blocker_codes: tuple[str, ...]
    source_exposure_result_hash: str
    concentration_policy_fingerprint_sha256: str | None
    proposal_count: int | None
    independent_cluster_count: int | None
    total_gross_bps: int | None
    largest_cluster_share_bps_ceiling: int | None
    hhi_ppm_ceiling: int | None
    effective_cluster_count_milli_floor: int | None


def _is_plain_int(value: object) -> bool:
    return type(value) is int


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _canonical_sha256(payload: object) -> str | None:
    try:
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None
    return hashlib.sha256(encoded).hexdigest()


def _source_result_payload(
    result: exposure_preflight.ClusterExposurePreflightResultV1,
) -> dict[str, Any]:
    return {
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


def _source_result_is_valid(
    result: object,
) -> bool:
    if not isinstance(
        result,
        exposure_preflight.ClusterExposurePreflightResultV1,
    ):
        return False
    if (
        result.contract_version != exposure_preflight.CONTRACT_VERSION
        or result.permission_state
        != exposure_preflight.PERMISSION_STATE_UNAUTHORIZED
        or result.permission is not False
        or result.research_only is not True
        or not _is_hash(result.source_batch_fingerprint_sha256)
        or type(result.blocker_codes) is not tuple
    ):
        return False
    if result.policy_result == exposure_preflight.POLICY_RESULT_UNKNOWN:
        return (
            bool(result.blocker_codes)
            and result.proposal_count is None
            and result.independent_cluster_count is None
            and result.total_gross_bps is None
            and result.cluster_gross_bps == ()
        )
    if result.policy_result not in {
        exposure_preflight.POLICY_RESULT_LIMIT_BREACH,
        exposure_preflight.POLICY_RESULT_WITHIN_LIMIT,
    } or not _is_hash(result.policy_fingerprint_sha256):
        return False
    if (
        not _is_plain_int(result.proposal_count)
        or result.proposal_count < 1
        or not _is_plain_int(result.independent_cluster_count)
        or not 1 <= result.independent_cluster_count <= result.proposal_count
        or not _is_plain_int(result.total_gross_bps)
        or result.total_gross_bps < 1
        or type(result.cluster_gross_bps) is not tuple
        or len(result.cluster_gross_bps) != result.independent_cluster_count
    ):
        return False
    normalized: list[tuple[str, int]] = []
    seen: set[str] = set()
    for item in result.cluster_gross_bps:
        if type(item) is not tuple or len(item) != 2:
            return False
        cluster_id, gross_bps = item
        if (
            not isinstance(cluster_id, str)
            or not _OPAQUE_ID_RE.fullmatch(cluster_id)
            or cluster_id in seen
            or not _is_plain_int(gross_bps)
            or gross_bps < 1
        ):
            return False
        seen.add(cluster_id)
        normalized.append((cluster_id, gross_bps))
    return (
        tuple(sorted(normalized)) == result.cluster_gross_bps
        and sum(gross_bps for _, gross_bps in normalized)
        == result.total_gross_bps
    )


def _validate_policy(
    policy: object,
) -> tuple[str, ...]:
    if not isinstance(policy, ClusterExposureConcentrationPolicyV1):
        return ("CONCENTRATION_POLICY_INVALID",)
    codes: list[str] = []
    if policy.policy_version != POLICY_VERSION:
        codes.append("CONCENTRATION_POLICY_VERSION_MISMATCH")
    if not isinstance(policy.policy_id, str) or not _POLICY_ID_RE.fullmatch(
        policy.policy_id
    ):
        codes.append("CONCENTRATION_POLICY_ID_INVALID")
    if (
        not _is_plain_int(policy.min_independent_clusters)
        or not 2 <= policy.min_independent_clusters <= 256
    ):
        codes.append("MIN_INDEPENDENT_CLUSTERS_INVALID")
    if (
        not _is_plain_int(policy.max_largest_cluster_share_bps)
        or not 1 <= policy.max_largest_cluster_share_bps <= SHARE_SCALE_BPS
    ):
        codes.append("MAX_LARGEST_CLUSTER_SHARE_INVALID")
    if (
        not _is_plain_int(policy.max_hhi_ppm)
        or not 1 <= policy.max_hhi_ppm <= HHI_SCALE_PPM
    ):
        codes.append("MAX_CLUSTER_HHI_INVALID")
    return tuple(codes)


def _policy_fingerprint(
    policy: ClusterExposureConcentrationPolicyV1,
) -> str | None:
    return _canonical_sha256(
        {
            "max_hhi_ppm": policy.max_hhi_ppm,
            "max_largest_cluster_share_bps": (
                policy.max_largest_cluster_share_bps
            ),
            "min_independent_clusters": policy.min_independent_clusters,
            "policy_id": policy.policy_id,
            "policy_version": policy.policy_version,
        }
    )


def _ceiling_divide(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def _no_metrics_result(
    *,
    status: str,
    blocker_codes: tuple[str, ...],
    source_result_hash: str,
    policy_fingerprint: str | None,
) -> ClusterExposureConcentrationResultV1:
    return ClusterExposureConcentrationResultV1(
        contract_version=CONTRACT_VERSION,
        status=status,
        permission_state=PERMISSION_STATE_UNAUTHORIZED,
        permission=False,
        research_only=True,
        blocker_codes=blocker_codes,
        source_exposure_result_hash=source_result_hash,
        concentration_policy_fingerprint_sha256=policy_fingerprint,
        proposal_count=None,
        independent_cluster_count=None,
        total_gross_bps=None,
        largest_cluster_share_bps_ceiling=None,
        hhi_ppm_ceiling=None,
        effective_cluster_count_milli_floor=None,
    )


def evaluate_cluster_exposure_concentration_from_verified_batch_v1(
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    concentration_policy: ClusterExposureConcentrationPolicyV1,
    *,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> ClusterExposureConcentrationResultV1 | None:
    """Evaluate concentration only after recomputing the exact exposure path."""

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
    if source_result is None or not _source_result_is_valid(source_result):
        return None
    source_result_hash = _canonical_sha256(_source_result_payload(source_result))
    if source_result_hash is None:
        return None

    policy_codes = _validate_policy(concentration_policy)
    policy_fingerprint = (
        _policy_fingerprint(concentration_policy) if not policy_codes else None
    )
    unknown_codes = list(policy_codes)
    if source_result.policy_result == exposure_preflight.POLICY_RESULT_UNKNOWN:
        unknown_codes.append("UPSTREAM_EXPOSURE_CONTRACT_UNKNOWN")
    if unknown_codes:
        return _no_metrics_result(
            status=STATUS_UNKNOWN,
            blocker_codes=tuple(unknown_codes),
            source_result_hash=source_result_hash,
            policy_fingerprint=policy_fingerprint,
        )
    if source_result.policy_result == exposure_preflight.POLICY_RESULT_LIMIT_BREACH:
        return _no_metrics_result(
            status=STATUS_UPSTREAM_LIMIT_BREACH,
            blocker_codes=("UPSTREAM_EXPOSURE_LIMIT_BREACH",),
            source_result_hash=source_result_hash,
            policy_fingerprint=policy_fingerprint,
        )

    cluster_gross_values = [
        gross_bps for _, gross_bps in source_result.cluster_gross_bps
    ]
    total_gross_bps = source_result.total_gross_bps
    assert isinstance(total_gross_bps, int)
    largest_cluster_gross_bps = max(cluster_gross_values)
    sum_of_squares = sum(value * value for value in cluster_gross_values)
    total_squared = total_gross_bps * total_gross_bps

    largest_share_bps = _ceiling_divide(
        largest_cluster_gross_bps * SHARE_SCALE_BPS,
        total_gross_bps,
    )
    hhi_ppm = _ceiling_divide(
        sum_of_squares * HHI_SCALE_PPM,
        total_squared,
    )
    effective_cluster_count_milli = (
        total_squared * EFFECTIVE_CLUSTER_SCALE_MILLI // sum_of_squares
    )

    blocker_codes: list[str] = []
    if (
        source_result.independent_cluster_count
        < concentration_policy.min_independent_clusters
    ):
        blocker_codes.append("INDEPENDENT_CLUSTER_COUNT_BELOW_MINIMUM")
    if largest_share_bps > concentration_policy.max_largest_cluster_share_bps:
        blocker_codes.append("LARGEST_CLUSTER_SHARE_LIMIT_EXCEEDED")
    if hhi_ppm > concentration_policy.max_hhi_ppm:
        blocker_codes.append("CLUSTER_HHI_LIMIT_EXCEEDED")

    return ClusterExposureConcentrationResultV1(
        contract_version=CONTRACT_VERSION,
        status=(
            STATUS_CONCENTRATION_LIMIT_BREACH
            if blocker_codes
            else STATUS_WITHIN_CONCENTRATION_LIMIT
        ),
        permission_state=PERMISSION_STATE_UNAUTHORIZED,
        permission=False,
        research_only=True,
        blocker_codes=tuple(blocker_codes),
        source_exposure_result_hash=source_result_hash,
        concentration_policy_fingerprint_sha256=policy_fingerprint,
        proposal_count=source_result.proposal_count,
        independent_cluster_count=source_result.independent_cluster_count,
        total_gross_bps=total_gross_bps,
        largest_cluster_share_bps_ceiling=largest_share_bps,
        hhi_ppm_ceiling=hhi_ppm,
        effective_cluster_count_milli_floor=effective_cluster_count_milli,
    )


__all__ = [
    "CONTRACT_VERSION",
    "POLICY_VERSION",
    "STATUS_CONCENTRATION_LIMIT_BREACH",
    "STATUS_UNKNOWN",
    "STATUS_UPSTREAM_LIMIT_BREACH",
    "STATUS_WITHIN_CONCENTRATION_LIMIT",
    "ClusterExposureConcentrationPolicyV1",
    "ClusterExposureConcentrationResultV1",
    "evaluate_cluster_exposure_concentration_from_verified_batch_v1",
]
