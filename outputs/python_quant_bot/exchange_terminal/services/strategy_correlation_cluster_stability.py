"""Consumer-only stability gate for within-cluster correlation topology."""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_violations,
)
from exchange_terminal.services.strategy_correlation_cluster_complete_link import (
    GATE_SCHEMA_VERSION as COMPLETE_LINK_GATE_SCHEMA_VERSION,
    verify_correlation_cluster_gate_v2,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    ABSOLUTE_PEARSON_THRESHOLD,
    EFFECTIVE_SAMPLE_METHOD,
    MINIMUM_EFFECTIVE_OBSERVATIONS,
    STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION,
    verify_strategy_correlation_uncertainty_audit,
)


POLICY_SCHEMA_VERSION = "strategy-correlation-cluster-stability-policy-v1"
AUDIT_SCHEMA_VERSION = "strategy-correlation-cluster-stability-audit-v1"
GATE_SCHEMA_VERSION = "strategy-correlation-cluster-stability-gate-v1"
POLICY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-policy-v1-verification-v1"
)
GATE_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-gate-v1-verification-v1"
)
FAMILY_SCOPE = "WITHIN_CLUSTER_PAIRS_ONLY"
CORRECTION_METHOD = "BONFERRONI_TWO_SIDED_FWER_V1"
FAMILYWISE_CONFIDENCE_LEVEL = 0.95
STABILITY_RULE = "ADJUSTED_ABSOLUTE_INTERVAL_LOWER_GTE_THRESHOLD"

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}


def build_strategy_correlation_cluster_stability_policy() -> dict[str, Any]:
    policy = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "family_scope": FAMILY_SCOPE,
        "correction_method": CORRECTION_METHOD,
        "familywise_confidence_level": FAMILYWISE_CONFIDENCE_LEVEL,
        "per_pair_alpha_formula": "0.05 / within_cluster_pair_count",
        "critical_value_formula": (
            "NORMAL_INV_CDF(1 - 0.05 / (2 * within_cluster_pair_count))"
        ),
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "minimum_effective_observations": MINIMUM_EFFECTIVE_OBSERVATIONS,
        "effective_sample_method": EFFECTIVE_SAMPLE_METHOD,
        "source_audit_schema_version": (
            STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION
        ),
        "source_gate_schema_version": COMPLETE_LINK_GATE_SCHEMA_VERSION,
        "stability_rule": STABILITY_RULE,
        "singleton_cluster_rule": "NO_INTERNAL_PAIR_REQUIRED",
        "source_block_action": "PRESERVE_BLOCK",
        "complete_link_block_action": "PRESERVE_BLOCK",
        "descriptive_only": True,
        "parameter_selection_allowed": False,
        "report_integration_status": "NOT_IMPLEMENTED",
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(policy, "policy_hash")


def verify_strategy_correlation_cluster_stability_policy(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    expected = build_strategy_correlation_cluster_stability_policy()
    if type(document) is not dict:
        blockers.append("stability_policy_invalid")
    else:
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
        if not strict_json_contract_equal(document, expected):
            blockers.append("stability_policy_contract_invalid")
    return {
        "schema_version": POLICY_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "descriptive_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def _pair_key(left: Any, right: Any) -> tuple[str, str] | None:
    if type(left) is not str or type(right) is not str or left == right:
        return None
    return tuple(sorted((left, right)))


def _pair_matrix_exactly_bound(
    source_uncertainty_audit: Any,
    correlation_matrix: Any,
) -> bool:
    if type(source_uncertainty_audit) is not dict or type(correlation_matrix) is not dict:
        return False
    source_pairs = source_uncertainty_audit.get("pairs")
    matrix_pairs = correlation_matrix.get("pairs")
    if type(source_pairs) is not list or type(matrix_pairs) is not list:
        return False
    source_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    matrix_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for pair in source_pairs:
        key = (
            _pair_key(pair.get("left_symbol"), pair.get("right_symbol"))
            if type(pair) is dict
            else None
        )
        if key is None or key in source_by_key:
            return False
        source_by_key[key] = pair
    for pair in matrix_pairs:
        key = (
            _pair_key(pair.get("left_symbol"), pair.get("right_symbol"))
            if type(pair) is dict
            else None
        )
        if key is None or key in matrix_by_key:
            return False
        matrix_by_key[key] = pair
    if set(source_by_key) != set(matrix_by_key):
        return False
    return all(
        strict_json_contract_equal(
            source_by_key[key].get("correlation"),
            matrix_by_key[key].get("pearson_correlation"),
        )
        and strict_json_contract_equal(
            source_by_key[key].get("overlap_observations"),
            matrix_by_key[key].get("overlap_observations"),
        )
        for key in source_by_key
    )


def _adjusted_absolute_interval(
    correlation: float,
    effective_observations: float,
    critical_value: float,
) -> tuple[float, float] | None:
    if (
        not math.isfinite(correlation)
        or not math.isfinite(effective_observations)
        or abs(correlation) > 1.0
        or effective_observations <= 3.0
    ):
        return None
    if abs(correlation) == 1.0:
        return 1.0, 1.0
    center = math.atanh(correlation)
    margin = critical_value / math.sqrt(effective_observations - 3.0)
    lower = math.tanh(center - margin)
    upper = math.tanh(center + margin)
    absolute_lower = 0.0 if lower <= 0.0 <= upper else min(abs(lower), abs(upper))
    absolute_upper = max(abs(lower), abs(upper))
    return round(absolute_lower, 12), round(absolute_upper, 12)


def evaluate_strategy_correlation_cluster_stability_gate(
    source_uncertainty_audit: Any,
    complete_link_gate: Any,
    *,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    policy = build_strategy_correlation_cluster_stability_policy()
    source_verification = (
        verify_strategy_correlation_uncertainty_audit(source_uncertainty_audit)
        if type(source_uncertainty_audit) is dict
        else {"status": "BLOCK"}
    )
    try:
        complete_link_verification = verify_correlation_cluster_gate_v2(
            complete_link_gate,
            preregistration=preregistration,
            correlation_matrix=correlation_matrix,
            selection_cells=selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (TypeError, ValueError):
        complete_link_verification = {"status": "BLOCK"}

    replay = (
        source_uncertainty_audit.get("matrix_replay")
        if type(source_uncertainty_audit) is dict
        else None
    )
    replay_preregistration = (
        replay.get("preregistration") if type(replay) is dict else None
    )
    input_binding = {
        "source_uncertainty_audit_verified": (
            source_verification.get("status") == "PASS"
        ),
        "complete_link_gate_verified": (
            complete_link_verification.get("status") == "PASS"
        ),
        "preregistration_exactly_bound": strict_json_contract_equal(
            replay_preregistration,
            preregistration,
        ),
        "pair_matrix_exactly_bound": _pair_matrix_exactly_bound(
            source_uncertainty_audit,
            correlation_matrix,
        ),
        "strategy_identity_bound": (
            type(complete_link_gate) is dict
            and complete_link_gate.get("strategy_id") == strategy_id
            and complete_link_gate.get("variant_id") == variant_id
            and complete_link_gate.get("lane") == lane
        ),
    }

    pairs = (
        source_uncertainty_audit.get("pairs")
        if type(source_uncertainty_audit) is dict
        and type(source_uncertainty_audit.get("pairs")) is list
        else []
    )
    within_pairs = [
        pair
        for pair in pairs
        if type(pair) is dict and pair.get("cross_cluster") is False
    ]
    family_size = len(within_pairs)
    critical_value = (
        NormalDist().inv_cdf(1.0 - 0.05 / (2.0 * family_size))
        if family_size
        else None
    )
    pair_results: list[dict[str, Any]] = []
    for pair in within_pairs:
        correlation = pair.get("correlation")
        effective_observations = pair.get("effective_observations")
        interval = (
            _adjusted_absolute_interval(
                float(correlation),
                float(effective_observations),
                float(critical_value),
            )
            if type(correlation) in {int, float}
            and type(effective_observations) in {int, float}
            and critical_value is not None
            else None
        )
        if (
            interval is None
            or float(effective_observations) < MINIMUM_EFFECTIVE_OBSERVATIONS
        ):
            classification = "INSUFFICIENT_EFFECTIVE_SAMPLE"
        elif interval[0] >= ABSOLUTE_PEARSON_THRESHOLD:
            classification = "STABLE_HIGH"
        else:
            classification = "UNSTABLE_THRESHOLD"
        pair_results.append(
            {
                "cluster_id": pair.get("left_cluster_id"),
                "left_symbol": pair.get("left_symbol"),
                "right_symbol": pair.get("right_symbol"),
                "correlation": correlation,
                "absolute_correlation": pair.get("absolute_correlation"),
                "overlap_observations": pair.get("overlap_observations"),
                "effective_observations": effective_observations,
                "source_classification": pair.get("classification"),
                "adjusted_absolute_interval_lower": (
                    interval[0] if interval is not None else None
                ),
                "adjusted_absolute_interval_upper": (
                    interval[1] if interval is not None else None
                ),
                "classification": classification,
                "status": "PASS" if classification == "STABLE_HIGH" else "BLOCK",
            }
        )

    clusters = (
        preregistration.get("clusters")
        if type(preregistration) is dict
        and type(preregistration.get("clusters")) is list
        else []
    )
    cluster_results: list[dict[str, Any]] = []
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id") if type(cluster) is dict else None
        results = [item for item in pair_results if item["cluster_id"] == cluster_id]
        stable_count = sum(item["status"] == "PASS" for item in results)
        cluster_results.append(
            {
                "cluster_id": cluster_id,
                "member_count": (
                    len(cluster.get("members", [])) if type(cluster) is dict else 0
                ),
                "within_pair_count": len(results),
                "stable_pair_count": stable_count,
                "status": "PASS" if stable_count == len(results) else "BLOCK",
                "interpretation": (
                    "NO_INTERNAL_PAIR" if not results else "ALL_INTERNAL_PAIRS_REQUIRED"
                ),
            }
        )

    blockers = [name for name, passed in input_binding.items() if not passed]
    if type(source_uncertainty_audit) is not dict or source_uncertainty_audit.get(
        "status"
    ) != "PASS":
        blockers.append("source_uncertainty_audit_blocked")
    if type(complete_link_gate) is not dict or complete_link_gate.get("status") != "PASS":
        blockers.append("complete_link_gate_blocked")
    blockers.extend(
        "within_cluster_pair_not_stable:"
        + ":".join(
            str(item[field])
            for field in ("cluster_id", "left_symbol", "right_symbol")
        )
        for item in pair_results
        if item["status"] != "PASS"
    )
    blockers = list(dict.fromkeys(blockers))
    audit = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "source_uncertainty_audit_hash": (
            source_uncertainty_audit.get("audit_hash")
            if type(source_uncertainty_audit) is dict
            else None
        ),
        "complete_link_gate_hash": (
            complete_link_gate.get("gate_hash")
            if type(complete_link_gate) is dict
            else None
        ),
        "preregistration_hash": (
            preregistration.get("preregistration_hash")
            if type(preregistration) is dict
            else None
        ),
        "matrix_hash": (
            correlation_matrix.get("matrix_hash")
            if type(correlation_matrix) is dict
            else None
        ),
        "policy": policy,
        "policy_hash": policy["policy_hash"],
        "family_scope": FAMILY_SCOPE,
        "within_cluster_pair_count": family_size,
        "bonferroni_critical_value": (
            round(critical_value, 12) if critical_value is not None else None
        ),
        "input_binding": input_binding,
        "pair_results": pair_results,
        "cluster_results": cluster_results,
        "blockers": blockers,
        "status": "PASS" if not blockers else "BLOCK",
        "consumer_only": True,
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    audit = seal_strict_canonical_document(audit, "audit_hash")
    tiers = [
        {
            "tier_id": "SOURCE_CONTRACTS",
            "status": (
                "PASS"
                if input_binding["source_uncertainty_audit_verified"]
                and input_binding["complete_link_gate_verified"]
                else "BLOCK"
            ),
        },
        {
            "tier_id": "INPUT_BINDING",
            "status": "PASS" if all(input_binding.values()) else "BLOCK",
        },
        {
            "tier_id": "WITHIN_CLUSTER_STABILITY",
            "status": audit["status"],
        },
    ]
    gate = {
        "schema_version": GATE_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "variant_id": variant_id,
        "lane": lane,
        "stability_audit": audit,
        "stability_audit_hash": audit["audit_hash"],
        "policy_hash": policy["policy_hash"],
        "tiers": tiers,
        "first_blocking_tier": next(
            (tier["tier_id"] for tier in tiers if tier["status"] == "BLOCK"),
            None,
        ),
        "blockers": blockers,
        "status": audit["status"],
        "consumer_only": True,
        "requires_new_report_schema": True,
        "report_integration_status": "NOT_IMPLEMENTED",
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return seal_strict_canonical_document(gate, "gate_hash")


def verify_strategy_correlation_cluster_stability_gate(
    document: Any,
    *,
    source_uncertainty_audit: Any,
    complete_link_gate: Any,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    expected = evaluate_strategy_correlation_cluster_stability_gate(
        source_uncertainty_audit,
        complete_link_gate,
        preregistration=preregistration,
        correlation_matrix=correlation_matrix,
        selection_cells=selection_cells,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    if type(document) is not dict:
        blockers.append("cluster_stability_gate_invalid")
    else:
        if strict_research_authority_violations(document):
            blockers.append("research_authority_violation")
        if not strict_json_contract_equal(document, expected):
            blockers.append("cluster_stability_gate_contract_invalid")
    status = "PASS" if not blockers else "BLOCK"
    return {
        "schema_version": GATE_VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "decision": expected["status"] if status == "PASS" else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "report_integration_status": "NOT_IMPLEMENTED",
        "writer_available": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


__all__ = [
    "AUDIT_SCHEMA_VERSION",
    "GATE_SCHEMA_VERSION",
    "POLICY_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_stability_policy",
    "evaluate_strategy_correlation_cluster_stability_gate",
    "verify_strategy_correlation_cluster_stability_gate",
    "verify_strategy_correlation_cluster_stability_policy",
]
