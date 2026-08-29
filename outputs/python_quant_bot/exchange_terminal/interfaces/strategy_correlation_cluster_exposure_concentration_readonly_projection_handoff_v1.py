"""Exact handoff from ADR0375 to the unmounted concentration presenter."""

from __future__ import annotations

import json
import re
from typing import Any, Final, Mapping

from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_concentration_gate_v1
    as concentration_gate,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_concentration_readonly_projection_v1
    as readonly_projection,
)
from exchange_terminal.application import (
    strategy_correlation_history_covered_budget_universe_cluster_exposure_preflight_v1
    as exposure_preflight,
)


HANDOFF_SCHEMA_VERSION: Final = (
    "cluster-exposure-concentration-readonly-projection-verification-handoff-v1"
)
VERIFICATION_STATUS: Final = (
    "EXACTLY_VERIFIED_CONCENTRATION_READONLY_PROJECTION_V1"
)
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and _HEX64_RE.fullmatch(value) is not None


def _json_safe_clone(value: object) -> object | None:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return json.loads(encoded)
    except (TypeError, ValueError, UnicodeEncodeError, json.JSONDecodeError):
        return None


def build_cluster_exposure_concentration_readonly_projection_handoff_v1(
    readonly_projection_document: Any,
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
) -> dict[str, Any] | None:
    if (
        not isinstance(readonly_projection_document, Mapping)
        or not _is_hash(expected_readonly_projection_hash)
    ):
        return None
    try:
        verified = readonly_projection.verify_cluster_exposure_concentration_readonly_projection_from_verified_batch_v1(
            readonly_projection_document,
            batch_preflight_document,
            projection_preregistration,
            proposals,
            exposure_policy,
            concentration_policy,
            expected_readonly_projection_hash=expected_readonly_projection_hash,
            expected_batch_preflight_hash=expected_batch_preflight_hash,
            expected_projection_preregistration_hash=(
                expected_projection_preregistration_hash
            ),
            projection_verification_context=projection_verification_context,
        )
    except (KeyError, TypeError, ValueError):
        return None
    if not verified:
        return None
    cloned = _json_safe_clone(dict(readonly_projection_document))
    if not isinstance(cloned, dict):
        return None
    return {
        "schema_version": HANDOFF_SCHEMA_VERSION,
        "verification_status": VERIFICATION_STATUS,
        "expected_readonly_projection_hash": expected_readonly_projection_hash,
        "projection": cloned,
    }


def verify_cluster_exposure_concentration_readonly_projection_handoff_v1(
    envelope: Any,
    readonly_projection_document: Any,
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
    expected = build_cluster_exposure_concentration_readonly_projection_handoff_v1(
        readonly_projection_document,
        batch_preflight_document,
        projection_preregistration,
        proposals,
        exposure_policy,
        concentration_policy,
        expected_readonly_projection_hash=expected_readonly_projection_hash,
        expected_batch_preflight_hash=expected_batch_preflight_hash,
        expected_projection_preregistration_hash=(
            expected_projection_preregistration_hash
        ),
        projection_verification_context=projection_verification_context,
    )
    return (
        isinstance(envelope, Mapping)
        and expected is not None
        and dict(envelope) == expected
    )


__all__ = [
    "HANDOFF_SCHEMA_VERSION",
    "VERIFICATION_STATUS",
    "build_cluster_exposure_concentration_readonly_projection_handoff_v1",
    "verify_cluster_exposure_concentration_readonly_projection_handoff_v1",
]
