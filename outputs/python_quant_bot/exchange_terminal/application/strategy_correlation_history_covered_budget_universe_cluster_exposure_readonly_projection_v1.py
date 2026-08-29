"""Hash-only read-only projection for verified cluster exposure evidence.

The public document is rebuilt from the exact ADR0370 verified-batch call path.
Raw symbols and cluster ids participate in the source-result hash but are never
copied into the projection.  This module is unmounted and grants no authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Final, Mapping

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_source_receipt_adapter_v1
    as source_adapter,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1
    as exposure_preflight,
)


PROJECTION_SCHEMA_VERSION: Final = (
    "strategy-correlation-history-covered-budget-universe-"
    "cluster-exposure-readonly-projection-v1"
)
STATIC_FINGERPRINT: Final = (
    "20260824-cluster-exposure-readonly-projection-v1-"
    "verified-batch-hash-only-unmounted-permission-lock-1"
)
CONSUMER_STATUS: Final = "UNMOUNTED_READONLY_CLUSTER_EXPOSURE_CANDIDATE"

PUBLIC_STATUS_UNKNOWN: Final = "UNKNOWN"
PUBLIC_STATUS_LIMIT_BREACH: Final = (
    "BLOCKED_PREREGISTERED_CLUSTER_EXPOSURE_LIMIT"
)
PUBLIC_STATUS_WITHIN_LIMIT: Final = (
    "OBSERVED_WITHIN_PREREGISTERED_CLUSTER_EXPOSURE_LIMIT"
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")

_LIMIT_BLOCKER_ORDER = (
    "PROPOSAL_COUNT_LIMIT_EXCEEDED",
    "SINGLE_PROPOSAL_GROSS_LIMIT_EXCEEDED",
    "CLUSTER_GROSS_LIMIT_EXCEEDED",
    "PORTFOLIO_GROSS_LIMIT_EXCEEDED",
)

_ALLOWED_POLICY_BLOCKER_CODES = frozenset(
    {
        "SOURCE_RECEIPT_INVALID",
        "SOURCE_RECEIPT_VERSION_MISMATCH",
        "SOURCE_PRODUCER_VERSION_MISMATCH",
        "SOURCE_BATCH_FINGERPRINT_INVALID",
        "SOURCE_NOT_STRUCTURALLY_COMPLETE",
        "SOURCE_PERMISSION_MUST_REMAIN_FALSE",
        "SOURCE_CLUSTER_MAP_INVALID",
        "SOURCE_SYMBOL_INVALID",
        "SOURCE_CLUSTER_ID_INVALID",
        "SOURCE_CLUSTER_MAP_DUPLICATE_SYMBOL",
        "SOURCE_CLUSTER_MAP_NOT_CANONICAL",
        "POLICY_INVALID",
        "POLICY_VERSION_MISMATCH",
        "POLICY_ID_INVALID",
        "POLICY_MAX_PROPOSALS_INVALID",
        "POLICY_PORTFOLIO_GROSS_LIMIT_INVALID",
        "POLICY_CLUSTER_GROSS_LIMIT_INVALID",
        "POLICY_SINGLE_PROPOSAL_GROSS_LIMIT_INVALID",
        "POLICY_LIMIT_ORDER_INVALID",
        "PROPOSAL_SET_NOT_CANONICAL",
        "PROPOSAL_SET_EMPTY",
        "PROPOSAL_SET_TOO_LARGE",
        "PROPOSAL_ROW_INVALID",
        "PROPOSAL_ID_INVALID",
        "DUPLICATE_PROPOSAL_ID",
        "PROPOSAL_SYMBOL_INVALID",
        "PROPOSAL_SYMBOL_NOT_IN_SOURCE_MAP",
        "PROPOSAL_GROSS_BPS_INVALID",
        "UNSPECIFIED_INPUT_FAILURE",
        *_LIMIT_BLOCKER_ORDER,
    }
)


def _authority_lock() -> dict[str, bool]:
    return {
        "consumer_registration_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "http_registration_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "readonly_projection_activation_allowed": False,
        "runtime_activation_allowed": False,
        "writer_allowed": False,
        "research_evidence_only": True,
    }


def _canonical_bytes(value: Any) -> bytes | None:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError):
        return None


def _digest(value: Any) -> str | None:
    encoded = _canonical_bytes(value)
    return hashlib.sha256(encoded).hexdigest() if encoded is not None else None


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _is_plain_int(value: object) -> bool:
    return type(value) is int


def _result_payload(
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


def _valid_source_result(
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
        or len(result.blocker_codes) != len(set(result.blocker_codes))
        or any(
            not isinstance(code, str)
            or code not in _ALLOWED_POLICY_BLOCKER_CODES
            for code in result.blocker_codes
        )
    ):
        return False

    if result.policy_fingerprint_sha256 is not None and not _is_hash(
        result.policy_fingerprint_sha256
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
    }:
        return False
    if not _is_hash(result.policy_fingerprint_sha256):
        return False
    if (
        not _is_plain_int(result.proposal_count)
        or not 1 <= result.proposal_count <= exposure_preflight.MAX_PROPOSAL_ROWS
        or not _is_plain_int(result.independent_cluster_count)
        or not 1 <= result.independent_cluster_count <= result.proposal_count
        or not _is_plain_int(result.total_gross_bps)
        or result.total_gross_bps < 1
        or type(result.cluster_gross_bps) is not tuple
        or len(result.cluster_gross_bps) != result.independent_cluster_count
    ):
        return False

    normalized_clusters: list[tuple[str, int]] = []
    seen_cluster_ids: set[str] = set()
    for item in result.cluster_gross_bps:
        if type(item) is not tuple or len(item) != 2:
            return False
        cluster_id, gross_bps = item
        if (
            not isinstance(cluster_id, str)
            or not _OPAQUE_ID_RE.fullmatch(cluster_id)
            or cluster_id in seen_cluster_ids
            or not _is_plain_int(gross_bps)
            or gross_bps < 1
        ):
            return False
        seen_cluster_ids.add(cluster_id)
        normalized_clusters.append((cluster_id, gross_bps))
    if tuple(sorted(normalized_clusters)) != result.cluster_gross_bps:
        return False
    if sum(gross_bps for _, gross_bps in normalized_clusters) != result.total_gross_bps:
        return False

    if result.policy_result == exposure_preflight.POLICY_RESULT_WITHIN_LIMIT:
        return result.blocker_codes == ()
    return (
        bool(result.blocker_codes)
        and result.blocker_codes
        == tuple(
            code for code in _LIMIT_BLOCKER_ORDER if code in result.blocker_codes
        )
    )


def _public_status_and_path(policy_result: str) -> tuple[str, str, str]:
    if policy_result == exposure_preflight.POLICY_RESULT_LIMIT_BREACH:
        return (
            PUBLIC_STATUS_LIMIT_BREACH,
            "PREREGISTERED_CLUSTER_EXPOSURE_LIMIT_BREACH",
            "STRUCTURAL_POLICY_BREACH",
        )
    if policy_result == exposure_preflight.POLICY_RESULT_WITHIN_LIMIT:
        return (
            PUBLIC_STATUS_WITHIN_LIMIT,
            "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
            "PREREGISTERED_STRUCTURE_ONLY",
        )
    return (
        PUBLIC_STATUS_UNKNOWN,
        "SOURCE_OR_POLICY_CONTRACT_UNKNOWN",
        "UNVERIFIED",
    )


def _build_projection_from_result_v1(
    result: object,
) -> dict[str, Any] | None:
    if not _valid_source_result(result):
        return None
    assert isinstance(
        result,
        exposure_preflight.ClusterExposurePreflightResultV1,
    )
    result_hash = _digest(_result_payload(result))
    if result_hash is None:
        return None
    public_status, gap, maturity = _public_status_and_path(result.policy_result)
    maximum_cluster_gross_bps = (
        max(gross_bps for _, gross_bps in result.cluster_gross_bps)
        if result.cluster_gross_bps
        else None
    )
    core = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": public_status,
        "source": {
            "adapter_contract_version": source_adapter.ADAPTER_CONTRACT_VERSION,
            "cluster_exposure_result_hash": result_hash,
            "policy_fingerprint_sha256": result.policy_fingerprint_sha256,
            "source_batch_fingerprint_sha256": (
                result.source_batch_fingerprint_sha256
            ),
        },
        "decision_path": {
            "source": "ADR0370_EXACT_VERIFIED_BATCH_RECEIPT",
            "gap": gap,
            "maturity": maturity,
            "permission": "NOT_AUTHORIZED",
        },
        "summary": {
            "proposal_count": result.proposal_count,
            "independent_cluster_count": result.independent_cluster_count,
            "total_gross_bps": result.total_gross_bps,
            "maximum_cluster_gross_bps": maximum_cluster_gross_bps,
        },
        "policy_blocker_codes": list(result.blocker_codes),
        "blockers": list(result.blocker_codes)
        + [
            "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
            "READONLY_PROJECTION_NOT_REGISTERED",
            "PAPER_LIVE_UNAUTHORIZED",
        ],
        "facts": {
            "cluster_ids_redacted": True,
            "fresh_projected_evidence_completed": False,
            "profitability_claim_allowed": False,
            "raw_symbols_redacted": True,
            "structural_exposure_metrics_only": True,
            "synthetic_only": True,
            "within_limit_is_not_admission": True,
        },
        "authority": _authority_lock(),
    }
    projection_hash = _digest(core)
    if projection_hash is None:
        return None
    return {**core, "readonly_projection_hash": projection_hash}


def build_cluster_exposure_readonly_projection_from_verified_batch_v1(
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    policy: exposure_preflight.ClusterExposurePolicyV1,
    *,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> dict[str, Any] | None:
    """Recompute the exact verified path, then emit a redacted projection."""

    result = source_adapter.evaluate_cluster_exposure_from_verified_batch_v1(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        policy,
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    return _build_projection_from_result_v1(result) if result is not None else None


def verify_cluster_exposure_readonly_projection_from_verified_batch_v1(
    document: Any,
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    policy: exposure_preflight.ClusterExposurePolicyV1,
    *,
    expected_readonly_projection_hash: Any,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> bool:
    if not _is_hash(expected_readonly_projection_hash):
        return False
    expected = build_cluster_exposure_readonly_projection_from_verified_batch_v1(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        policy,
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    return (
        isinstance(document, Mapping)
        and expected is not None
        and expected.get("readonly_projection_hash")
        == expected_readonly_projection_hash
        and document.get("readonly_projection_hash")
        == expected_readonly_projection_hash
        and dict(document) == expected
    )


__all__ = [
    "CONSUMER_STATUS",
    "PROJECTION_SCHEMA_VERSION",
    "PUBLIC_STATUS_LIMIT_BREACH",
    "PUBLIC_STATUS_UNKNOWN",
    "PUBLIC_STATUS_WITHIN_LIMIT",
    "STATIC_FINGERPRINT",
    "build_cluster_exposure_readonly_projection_from_verified_batch_v1",
    "verify_cluster_exposure_readonly_projection_from_verified_batch_v1",
]
