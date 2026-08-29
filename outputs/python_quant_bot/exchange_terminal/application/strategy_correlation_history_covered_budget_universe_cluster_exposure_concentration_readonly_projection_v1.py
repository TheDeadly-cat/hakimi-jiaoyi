"""Hash-only read-only projection for ADR0374 concentration evidence.

The projection is rebuilt from the complete verified-batch concentration path.
It exposes only redacted structural metrics and allowlisted blocker codes.  It
has no runtime, HTTP, storage, pointer, paper, or live integration.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Final, Mapping

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_concentration_gate_v1
    as concentration_gate,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1
    as exposure_preflight,
)


PROJECTION_SCHEMA_VERSION: Final = (
    "strategy-correlation-history-covered-budget-universe-cluster-exposure-"
    "concentration-readonly-projection-v1"
)
STATIC_FINGERPRINT: Final = (
    "20260824-cluster-exposure-concentration-readonly-projection-v1-"
    "verified-batch-hash-only-unmounted-permission-lock-1"
)
CONSUMER_STATUS: Final = (
    "UNMOUNTED_READONLY_CLUSTER_EXPOSURE_CONCENTRATION_CANDIDATE"
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_CONCENTRATION_BLOCKER_ORDER = (
    "INDEPENDENT_CLUSTER_COUNT_BELOW_MINIMUM",
    "LARGEST_CLUSTER_SHARE_LIMIT_EXCEEDED",
    "CLUSTER_HHI_LIMIT_EXCEEDED",
)
_ALLOWED_BLOCKERS = frozenset(
    {
        "CONCENTRATION_POLICY_INVALID",
        "CONCENTRATION_POLICY_VERSION_MISMATCH",
        "CONCENTRATION_POLICY_ID_INVALID",
        "MIN_INDEPENDENT_CLUSTERS_INVALID",
        "MAX_LARGEST_CLUSTER_SHARE_INVALID",
        "MAX_CLUSTER_HHI_INVALID",
        "UPSTREAM_EXPOSURE_CONTRACT_UNKNOWN",
        "UPSTREAM_EXPOSURE_LIMIT_BREACH",
        *_CONCENTRATION_BLOCKER_ORDER,
    }
)


def _authority_lock() -> dict[str, bool]:
    return {
        "consumer_registration_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "diversification_claim_allowed": False,
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
    result: concentration_gate.ClusterExposureConcentrationResultV1,
) -> dict[str, Any]:
    return {
        "blocker_codes": list(result.blocker_codes),
        "concentration_policy_fingerprint_sha256": (
            result.concentration_policy_fingerprint_sha256
        ),
        "contract_version": result.contract_version,
        "effective_cluster_count_milli_floor": (
            result.effective_cluster_count_milli_floor
        ),
        "hhi_ppm_ceiling": result.hhi_ppm_ceiling,
        "independent_cluster_count": result.independent_cluster_count,
        "largest_cluster_share_bps_ceiling": (
            result.largest_cluster_share_bps_ceiling
        ),
        "permission": result.permission,
        "permission_state": result.permission_state,
        "proposal_count": result.proposal_count,
        "research_only": result.research_only,
        "source_exposure_result_hash": result.source_exposure_result_hash,
        "status": result.status,
        "total_gross_bps": result.total_gross_bps,
    }


def _metrics_are_null(
    result: concentration_gate.ClusterExposureConcentrationResultV1,
) -> bool:
    return all(
        value is None
        for value in (
            result.proposal_count,
            result.independent_cluster_count,
            result.total_gross_bps,
            result.largest_cluster_share_bps_ceiling,
            result.hhi_ppm_ceiling,
            result.effective_cluster_count_milli_floor,
        )
    )


def _valid_metrics(
    result: concentration_gate.ClusterExposureConcentrationResultV1,
) -> bool:
    return (
        _is_plain_int(result.proposal_count)
        and result.proposal_count >= 1
        and _is_plain_int(result.independent_cluster_count)
        and 1 <= result.independent_cluster_count <= result.proposal_count
        and _is_plain_int(result.total_gross_bps)
        and result.total_gross_bps >= 1
        and _is_plain_int(result.largest_cluster_share_bps_ceiling)
        and 1
        <= result.largest_cluster_share_bps_ceiling
        <= concentration_gate.SHARE_SCALE_BPS
        and _is_plain_int(result.hhi_ppm_ceiling)
        and 1 <= result.hhi_ppm_ceiling <= concentration_gate.HHI_SCALE_PPM
        and _is_plain_int(result.effective_cluster_count_milli_floor)
        and concentration_gate.EFFECTIVE_CLUSTER_SCALE_MILLI
        <= result.effective_cluster_count_milli_floor
        <= result.independent_cluster_count
        * concentration_gate.EFFECTIVE_CLUSTER_SCALE_MILLI
    )


def _valid_result(result: object) -> bool:
    if not isinstance(
        result,
        concentration_gate.ClusterExposureConcentrationResultV1,
    ):
        return False
    if (
        result.contract_version != concentration_gate.CONTRACT_VERSION
        or result.permission_state
        != concentration_gate.PERMISSION_STATE_UNAUTHORIZED
        or result.permission is not False
        or result.research_only is not True
        or not _is_hash(result.source_exposure_result_hash)
        or type(result.blocker_codes) is not tuple
        or len(result.blocker_codes) != len(set(result.blocker_codes))
        or any(code not in _ALLOWED_BLOCKERS for code in result.blocker_codes)
    ):
        return False
    if (
        result.concentration_policy_fingerprint_sha256 is not None
        and not _is_hash(result.concentration_policy_fingerprint_sha256)
    ):
        return False

    if result.status == concentration_gate.STATUS_UNKNOWN:
        return bool(result.blocker_codes) and _metrics_are_null(result)
    if result.status == concentration_gate.STATUS_UPSTREAM_LIMIT_BREACH:
        return (
            result.concentration_policy_fingerprint_sha256 is not None
            and result.blocker_codes == ("UPSTREAM_EXPOSURE_LIMIT_BREACH",)
            and _metrics_are_null(result)
        )
    if result.status not in {
        concentration_gate.STATUS_CONCENTRATION_LIMIT_BREACH,
        concentration_gate.STATUS_WITHIN_CONCENTRATION_LIMIT,
    }:
        return False
    if (
        not _is_hash(result.concentration_policy_fingerprint_sha256)
        or not _valid_metrics(result)
    ):
        return False
    if result.status == concentration_gate.STATUS_WITHIN_CONCENTRATION_LIMIT:
        return result.blocker_codes == ()
    return (
        bool(result.blocker_codes)
        and result.blocker_codes
        == tuple(
            code
            for code in _CONCENTRATION_BLOCKER_ORDER
            if code in result.blocker_codes
        )
    )


def _decision_path(status: str) -> tuple[str, str]:
    if status == concentration_gate.STATUS_UPSTREAM_LIMIT_BREACH:
        return (
            "UPSTREAM_ABSOLUTE_EXPOSURE_LIMIT_BREACH",
            "STRUCTURAL_UPSTREAM_BLOCK",
        )
    if status == concentration_gate.STATUS_CONCENTRATION_LIMIT_BREACH:
        return (
            "PREREGISTERED_CLUSTER_CONCENTRATION_LIMIT_BREACH",
            "STRUCTURAL_CONCENTRATION_POLICY_BREACH",
        )
    if status == concentration_gate.STATUS_WITHIN_CONCENTRATION_LIMIT:
        return (
            "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
            "PREREGISTERED_CONCENTRATION_STRUCTURE_ONLY",
        )
    return ("SOURCE_OR_CONCENTRATION_POLICY_UNKNOWN", "UNVERIFIED")


def _build_projection_from_result_v1(result: object) -> dict[str, Any] | None:
    if not _valid_result(result):
        return None
    assert isinstance(
        result,
        concentration_gate.ClusterExposureConcentrationResultV1,
    )
    result_hash = _digest(_result_payload(result))
    if result_hash is None:
        return None
    gap, maturity = _decision_path(result.status)
    core = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "consumer_status": CONSUMER_STATUS,
        "registered": False,
        "status": result.status,
        "source": {
            "concentration_gate_contract_version": (
                concentration_gate.CONTRACT_VERSION
            ),
            "concentration_result_hash": result_hash,
            "concentration_policy_fingerprint_sha256": (
                result.concentration_policy_fingerprint_sha256
            ),
            "source_exposure_result_hash": result.source_exposure_result_hash,
        },
        "decision_path": {
            "source": "ADR0374_EXACT_VERIFIED_BATCH_CONCENTRATION",
            "gap": gap,
            "maturity": maturity,
            "permission": "NOT_AUTHORIZED",
        },
        "summary": {
            "proposal_count": result.proposal_count,
            "independent_cluster_count": result.independent_cluster_count,
            "total_gross_bps": result.total_gross_bps,
            "largest_cluster_share_bps_ceiling": (
                result.largest_cluster_share_bps_ceiling
            ),
            "hhi_ppm_ceiling": result.hhi_ppm_ceiling,
            "effective_cluster_count_milli_floor": (
                result.effective_cluster_count_milli_floor
            ),
        },
        "policy_blocker_codes": list(result.blocker_codes),
        "blockers": list(result.blocker_codes)
        + [
            "FRESH_PROJECTED_EVIDENCE_INCOMPLETE",
            "READONLY_PROJECTION_NOT_REGISTERED",
            "PAPER_LIVE_UNAUTHORIZED",
        ],
        "facts": {
            "concentration_metrics_structural_only": True,
            "diversification_quality_claim_allowed": False,
            "fresh_projected_evidence_completed": False,
            "profitability_claim_allowed": False,
            "raw_cluster_ids_redacted": True,
            "raw_symbols_redacted": True,
            "synthetic_only": True,
            "within_limit_is_not_admission": True,
        },
        "authority": _authority_lock(),
    }
    projection_hash = _digest(core)
    if projection_hash is None:
        return None
    return {**core, "readonly_projection_hash": projection_hash}


def build_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1(
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    concentration_policy: concentration_gate.ClusterExposureConcentrationPolicyV1,
    *,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> dict[str, Any] | None:
    result = concentration_gate.evaluate_cluster_exposure_concentration_from_verified_batch_v1(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        concentration_policy,
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    return _build_projection_from_result_v1(result) if result is not None else None


def verify_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1(
    document: Any,
    batch_preflight_document: Any,
    projection_preregistration: Any,
    proposals: tuple[exposure_preflight.ClusterExposureProposalV1, ...],
    exposure_policy: exposure_preflight.ClusterExposurePolicyV1,
    concentration_policy: concentration_gate.ClusterExposureConcentrationPolicyV1,
    *,
    expected_readonly_projection_hash: Any,
    expected_batch_preflight_hash: Any,
    expected_projection_preregistration_hash: Any,
    projection_verification_context: Any,
) -> bool:
    if not _is_hash(expected_readonly_projection_hash):
        return False
    expected = build_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1(
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        concentration_policy,
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
    "STATIC_FINGERPRINT",
    "build_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1",
    "verify_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1",
]
