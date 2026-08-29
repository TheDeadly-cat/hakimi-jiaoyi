from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .strategy_correlation_cross_lag_gate import (
    EVALUATION_SCHEMA,
    FAMILY_ALPHA,
    LAGS,
    MIN_ADJUSTED_ABSOLUTE_LOWER,
    MIN_EFFECTIVE_SAMPLE,
    MIN_OBSERVATION_COUNT,
    STATIC_FINGERPRINT as GATE_STATIC_FINGERPRINT,
)
from .strategy_correlation_cross_lag_direction_contract import (
    CONTRACT_SCHEMA as DIRECTION_CONTRACT_SCHEMA,
    LAG_DIRECTION_CONVENTION,
    build_strategy_correlation_cross_lag_direction_contract,
)
from .strategy_correlation_strata_registry import (
    BINDING_ASSESSMENT_SCHEMA,
    REGISTRY_ASSET_SCHEMA,
    verify_strategy_correlation_strata_registry_asset,
    verify_strategy_correlation_strata_registry_binding,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from .strict_governance_primitives import (
    strict_iso_date,
    strict_nonempty_string,
    strict_sha256,
    strict_utc_second_timestamp,
)


ADAPTER_SCHEMA = "strategy-correlation-cross-lag-registry-assignment-adapter-candidate-v1"
STATIC_FINGERPRINT = "20260821-cross-lag-registry-assignment-adapter-2"
MULTIPLICITY_POLICY = "BONFERRONI_GLOBAL_CROSS_STRATUM_PAIR_LAG_FAMILY"

_VALID_BLOCKERS = [
    "CROSS_LAG_PROTOCOL_REGISTRATION_UNBOUND",
]

_LOCKED_AUTHORITY = {
    "descriptive_only": True,
    "formal_preregistration_bound": False,
    "sequence_order_attested": False,
    "strata_timing_attested": False,
    "independence_proven": False,
    "count_as_independent_allowed": False,
    "candidate_binding_activation_allowed": False,
    "formal_registry_activation_allowed": False,
    "formal_registry_written": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
    "current_pointer_written": False,
    "paper_authorized": False,
    "live_order_allowed": False,
    "profitability_claim_allowed": False,
}


def _analytic_policy() -> dict[str, Any]:
    direction_contract = build_strategy_correlation_cross_lag_direction_contract()
    policy = {
        "source_gate_schema": EVALUATION_SCHEMA,
        "source_gate_static_fingerprint": GATE_STATIC_FINGERPRINT,
        "lag_family": list(LAGS),
        "lag_direction_contract_schema": DIRECTION_CONTRACT_SCHEMA,
        "lag_direction_contract_hash": direction_contract["contract_hash"],
        "lag_direction_convention": LAG_DIRECTION_CONVENTION,
        "family_alpha": str(FAMILY_ALPHA),
        "multiplicity_policy": MULTIPLICITY_POLICY,
        "minimum_observation_count": MIN_OBSERVATION_COUNT,
        "minimum_effective_sample_size": str(MIN_EFFECTIVE_SAMPLE),
        "minimum_adjusted_absolute_lower": str(MIN_ADJUSTED_ABSOLUTE_LOWER),
    }
    policy["policy_hash"] = strict_canonical_hash(policy)
    return policy


def _sealed_adapter(
    *,
    adapter_state: str,
    source_state: str,
    gap_state: str,
    maturity_state: str,
    blockers: list[str],
    source_preregistration_hash: str = "",
    strata_registration_hash: str = "",
    registry_asset_hash: str = "",
    registry_binding_assessment_hash: str = "",
    classification_source_hash: str = "",
    classification_effective_date: str = "",
    selection_cutoff_date: str = "",
    frozen_at: str = "",
    first_observation_timestamp: str = "",
    dimension_id: str = "",
    identity_set: list[str] | None = None,
    stratum_assignment: dict[str, str] | None = None,
) -> dict[str, Any]:
    identities = [] if identity_set is None else list(identity_set)
    assignment = {} if stratum_assignment is None else dict(stratum_assignment)
    return seal_strict_canonical_document(
        {
            "schema_version": ADAPTER_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "adapter_state": adapter_state,
            "source_state": source_state,
            "gap_state": gap_state,
            "maturity_state": maturity_state,
            "permission_state": "LOCKED",
            "registry_assignment_verified": adapter_state == "REGISTRY_ASSIGNMENT_VERIFIED_CANDIDATE",
            "protocol_registration_bound": False,
            "source_preregistration_hash": source_preregistration_hash,
            "strata_registration_hash": strata_registration_hash,
            "registry_asset_schema": REGISTRY_ASSET_SCHEMA,
            "registry_asset_hash": registry_asset_hash,
            "registry_binding_schema": BINDING_ASSESSMENT_SCHEMA,
            "registry_binding_assessment_hash": registry_binding_assessment_hash,
            "classification_source_hash": classification_source_hash,
            "classification_effective_date": classification_effective_date,
            "selection_cutoff_date": selection_cutoff_date,
            "frozen_at": frozen_at,
            "first_observation_timestamp": first_observation_timestamp,
            "dimension_id": dimension_id,
            "identity_count": len(identities),
            "stratum_count": len(set(assignment.values())),
            "identity_set": identities,
            "identity_set_hash": strict_canonical_hash(identities) if identities else "",
            "stratum_assignment": assignment,
            "stratum_assignment_hash": strict_canonical_hash(assignment) if assignment else "",
            "analytic_policy": _analytic_policy(),
            "blockers": list(blockers),
            "authority": dict(_LOCKED_AUTHORITY),
        },
        "adapter_hash",
    )


def _not_supplied_adapter() -> dict[str, Any]:
    return _sealed_adapter(
        adapter_state="NOT_SUPPLIED",
        source_state="NOT_SUPPLIED",
        gap_state="REGISTRY_EVIDENCE_NOT_SUPPLIED",
        maturity_state="NOT_EVALUATED",
        blockers=["REGISTRY_EVIDENCE_NOT_SUPPLIED"],
    )


def _unknown_adapter() -> dict[str, Any]:
    return _sealed_adapter(
        adapter_state="UNKNOWN",
        source_state="UNKNOWN",
        gap_state="REGISTRY_EVIDENCE_INVALID",
        maturity_state="UNKNOWN",
        blockers=["REGISTRY_EVIDENCE_INVALID"],
    )


def _utc_second(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _derive_assignment(
    source_preregistration: dict[str, Any],
    registry_asset: dict[str, Any],
    dimension_id: str,
) -> dict[str, str] | None:
    clusters = source_preregistration.get("clusters")
    symbols = source_preregistration.get("symbols")
    dimensions = registry_asset.get("dimensions")
    if not isinstance(clusters, list) or not isinstance(symbols, list) or not isinstance(dimensions, list):
        return None
    if not clusters or not symbols:
        return None

    cluster_members: dict[str, list[str]] = {}
    all_members: set[str] = set()
    for cluster in clusters:
        if not isinstance(cluster, dict):
            return None
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if not strict_nonempty_string(cluster_id) or cluster_id in cluster_members:
            return None
        if not isinstance(members, list) or not members:
            return None
        normalized_members: list[str] = []
        for member in members:
            if not strict_nonempty_string(member) or member in all_members:
                return None
            normalized_members.append(member)
            all_members.add(member)
        cluster_members[cluster_id] = normalized_members

    if any(not strict_nonempty_string(symbol) for symbol in symbols):
        return None
    if len(set(symbols)) != len(symbols) or set(symbols) != all_members:
        return None

    selected = [item for item in dimensions if isinstance(item, dict) and item.get("dimension_id") == dimension_id]
    if len(selected) != 1:
        return None
    strata = selected[0].get("strata")
    if not isinstance(strata, list) or len(strata) < 2:
        return None

    seen_strata: set[str] = set()
    seen_clusters: set[str] = set()
    assignment: dict[str, str] = {}
    for stratum in strata:
        if not isinstance(stratum, dict):
            return None
        stratum_id = stratum.get("stratum_id")
        cluster_ids = stratum.get("cluster_ids")
        if not strict_nonempty_string(stratum_id) or stratum_id in seen_strata:
            return None
        if not isinstance(cluster_ids, list) or not cluster_ids:
            return None
        seen_strata.add(stratum_id)
        for cluster_id in cluster_ids:
            if cluster_id not in cluster_members or cluster_id in seen_clusters:
                return None
            seen_clusters.add(cluster_id)
            for member in cluster_members[cluster_id]:
                assignment[member] = stratum_id

    if seen_clusters != set(cluster_members):
        return None
    if set(assignment) != set(symbols):
        return None
    return {identity: assignment[identity] for identity in sorted(assignment)}


def build_strategy_correlation_cross_lag_registry_assignment_adapter(
    registry_asset: Any,
    registry_binding_assessment: Any,
    *,
    source_preregistration: Any,
    strata_registration: Any,
    dimension_id: Any,
    selection_cutoff_date: Any,
    first_observation_timestamp: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
    expected_stratum_assignment_hash: Any,
) -> dict[str, Any]:
    """Verify frozen registry evidence and derive one exact gate assignment."""

    if registry_asset is None and registry_binding_assessment is None:
        return _not_supplied_adapter()
    if not all(
        isinstance(value, dict)
        for value in (
            registry_asset,
            registry_binding_assessment,
            source_preregistration,
            strata_registration,
        )
    ):
        return _unknown_adapter()
    if not strict_nonempty_string(dimension_id):
        return _unknown_adapter()
    if not strict_iso_date(selection_cutoff_date):
        return _unknown_adapter()
    if not strict_utc_second_timestamp(first_observation_timestamp):
        return _unknown_adapter()
    if not all(
        strict_sha256(value)
        for value in (
            expected_registry_asset_hash,
            expected_classification_source_hash,
            expected_stratum_assignment_hash,
        )
    ):
        return _unknown_adapter()

    try:
        asset_verification = verify_strategy_correlation_strata_registry_asset(
            registry_asset,
            source_preregistration=source_preregistration,
        )
        binding_verification = verify_strategy_correlation_strata_registry_binding(
            registry_binding_assessment,
            registry_asset=registry_asset,
            registration=strata_registration,
            source_preregistration=source_preregistration,
            selection_cutoff_date=selection_cutoff_date,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_classification_source_hash=expected_classification_source_hash,
        )
    except Exception:
        return _unknown_adapter()
    if asset_verification.get("status") != "PASS" or binding_verification.get("status") != "PASS":
        return _unknown_adapter()

    assignment = _derive_assignment(source_preregistration, registry_asset, dimension_id)
    if assignment is None or strict_canonical_hash(assignment) != expected_stratum_assignment_hash:
        return _unknown_adapter()
    frozen_at = registry_asset.get("frozen_at")
    if not strict_utc_second_timestamp(frozen_at):
        return _unknown_adapter()
    if _utc_second(frozen_at) > _utc_second(first_observation_timestamp):
        return _unknown_adapter()

    identities = sorted(assignment)
    return _sealed_adapter(
        adapter_state="REGISTRY_ASSIGNMENT_VERIFIED_CANDIDATE",
        source_state="OBSERVED",
        gap_state="PROTOCOL_REGISTRATION_UNBOUND",
        maturity_state="CANDIDATE_REGISTRY_BOUND_NOT_PROTOCOL_BOUND",
        blockers=_VALID_BLOCKERS,
        source_preregistration_hash=source_preregistration["preregistration_hash"],
        strata_registration_hash=strata_registration["registration_hash"],
        registry_asset_hash=registry_asset["registry_asset_hash"],
        registry_binding_assessment_hash=registry_binding_assessment["assessment_hash"],
        classification_source_hash=expected_classification_source_hash,
        classification_effective_date=registry_asset["effective_date"],
        selection_cutoff_date=selection_cutoff_date,
        frozen_at=frozen_at,
        first_observation_timestamp=first_observation_timestamp,
        dimension_id=dimension_id,
        identity_set=identities,
        stratum_assignment=assignment,
    )


def verify_strategy_correlation_cross_lag_registry_assignment_adapter(
    document: Any,
    registry_asset: Any,
    registry_binding_assessment: Any,
    *,
    source_preregistration: Any,
    strata_registration: Any,
    dimension_id: Any,
    selection_cutoff_date: Any,
    first_observation_timestamp: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
    expected_stratum_assignment_hash: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected = build_strategy_correlation_cross_lag_registry_assignment_adapter(
            registry_asset,
            registry_binding_assessment,
            source_preregistration=source_preregistration,
            strata_registration=strata_registration,
            dimension_id=dimension_id,
            selection_cutoff_date=selection_cutoff_date,
            first_observation_timestamp=first_observation_timestamp,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_classification_source_hash=expected_classification_source_hash,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
    except Exception:
        return False
    return strict_json_contract_equal(document, expected)
