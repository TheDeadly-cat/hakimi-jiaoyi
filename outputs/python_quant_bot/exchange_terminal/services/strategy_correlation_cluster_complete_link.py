from __future__ import annotations

from itertools import combinations
from typing import Any

try:
    from services.strategy_correlation_cluster_gate import (
        ABSOLUTE_PEARSON_THRESHOLD,
        MINIMUM_PAIR_OVERLAP,
        evaluate_correlation_cluster_gate,
        verify_correlation_cluster_preregistration,
        verify_correlation_matrix_contract,
    )
    from services.strict_canonical_json_hash import (
        strict_canonical_hash,
        strict_json_contract_equal,
    )
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_cluster_gate import (
        ABSOLUTE_PEARSON_THRESHOLD,
        MINIMUM_PAIR_OVERLAP,
        evaluate_correlation_cluster_gate,
        verify_correlation_cluster_preregistration,
        verify_correlation_matrix_contract,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_canonical_hash,
        strict_json_contract_equal,
    )


AUDIT_SCHEMA_VERSION = "strategy-correlation-cluster-complete-link-audit-v1"
AUDIT_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-complete-link-audit-verification-v1"
)
GATE_SCHEMA_VERSION = "strategy-correlation-cluster-gate-v2"
GATE_VERIFICATION_SCHEMA_VERSION = "strategy-correlation-cluster-gate-v2-verification-v1"
TOPOLOGY_RULE = "ALL_INTERNAL_PAIRS_MEET_ABSOLUTE_PEARSON_THRESHOLD"

_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _sha256(value: Any) -> str:
    return strict_canonical_hash(value)


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    return {**payload, field: _sha256(payload)}


def _verification(schema_version: str, blockers: list[str]) -> dict[str, Any]:
    unique = sorted(set(blockers))
    return {
        "schema_version": schema_version,
        "status": "PASS" if not unique else "BLOCK",
        "blockers": unique,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }


def build_correlation_cluster_complete_link_audit(
    preregistration: Any,
    correlation_matrix: Any,
) -> dict[str, Any]:
    expected_symbols = (
        list(preregistration.get("symbols") or [])
        if type(preregistration) is dict
        and type(preregistration.get("symbols")) is list
        else []
    )
    preregistration_verification = verify_correlation_cluster_preregistration(
        preregistration
    )
    try:
        matrix_verification = verify_correlation_matrix_contract(
            correlation_matrix,
            expected_symbols=expected_symbols,
        )
    except (TypeError, ValueError):
        matrix_verification = {
            "status": "BLOCK",
            "blockers": ["correlation_matrix_contract_invalid"],
        }

    blockers: list[str] = []
    if preregistration_verification.get("status") != "PASS":
        blockers.append("correlation_cluster_preregistration_invalid")
    if matrix_verification.get("status") != "PASS":
        blockers.append("correlation_matrix_contract_invalid")

    base: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "status": "BLOCK",
        "topology_rule": TOPOLOGY_RULE,
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
        "preregistration_hash": (
            str(preregistration.get("preregistration_hash") or "")
            if type(preregistration) is dict
            else ""
        ),
        "matrix_hash": (
            str(correlation_matrix.get("matrix_hash") or "")
            if type(correlation_matrix) is dict
            else ""
        ),
        "cluster_results": [],
        "internal_pair_conflicts": [],
        "blockers": sorted(set(blockers)),
        "requires_new_report_schema": True,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    if blockers:
        return _seal(base, "audit_hash")

    pair_index = {
        tuple(sorted((pair["left_symbol"], pair["right_symbol"]))): pair
        for pair in correlation_matrix["pairs"]
    }
    cluster_results: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    topology_blockers: list[str] = []

    for cluster in preregistration["clusters"]:
        members = list(cluster["members"])
        pair_results: list[dict[str, Any]] = []
        for left_symbol, right_symbol in combinations(members, 2):
            pair = pair_index[tuple(sorted((left_symbol, right_symbol)))]
            correlation = float(pair["pearson_correlation"])
            overlap = int(pair["overlap_observations"])
            pair_blockers: list[str] = []
            if overlap < MINIMUM_PAIR_OVERLAP:
                pair_blockers.append("internal_pair_overlap_insufficient")
                topology_blockers.append("cluster_internal_pair_overlap_insufficient")
            if abs(correlation) < ABSOLUTE_PEARSON_THRESHOLD:
                pair_blockers.append("internal_pair_below_absolute_threshold")
                topology_blockers.append("cluster_complete_link_threshold_not_met")
            pair_result = {
                "left_symbol": left_symbol,
                "right_symbol": right_symbol,
                "pearson_correlation": correlation,
                "overlap_observations": overlap,
                "status": "PASS" if not pair_blockers else "BLOCK",
                "blockers": sorted(set(pair_blockers)),
            }
            pair_results.append(pair_result)
            if pair_blockers:
                conflicts.append({"cluster_id": cluster["cluster_id"], **pair_result})

        qualifying_pair_count = sum(
            pair["status"] == "PASS" for pair in pair_results
        )
        cluster_results.append(
            {
                "cluster_id": cluster["cluster_id"],
                "members": members,
                "pair_count": len(pair_results),
                "qualifying_pair_count": qualifying_pair_count,
                "pair_results": pair_results,
                "status": (
                    "PASS" if qualifying_pair_count == len(pair_results) else "BLOCK"
                ),
            }
        )

    base.update(
        {
            "status": "PASS" if not topology_blockers else "BLOCK",
            "cluster_results": cluster_results,
            "internal_pair_conflicts": conflicts,
            "blockers": sorted(set(topology_blockers)),
        }
    )
    return _seal(base, "audit_hash")


def verify_correlation_cluster_complete_link_audit(
    document: Any,
    *,
    preregistration: Any,
    correlation_matrix: Any,
) -> dict[str, Any]:
    try:
        expected = build_correlation_cluster_complete_link_audit(
            preregistration,
            correlation_matrix,
        )
    except (KeyError, TypeError, ValueError):
        return _verification(
            AUDIT_VERIFICATION_SCHEMA_VERSION,
            ["complete_link_audit_source_invalid"],
        )
    blockers = (
        []
        if type(document) is dict
        and strict_json_contract_equal(document, expected)
        else [
        "complete_link_audit_contract_invalid"
        ]
    )
    return _verification(AUDIT_VERIFICATION_SCHEMA_VERSION, blockers)


def evaluate_correlation_cluster_gate_v2(
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    *,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    legacy_gate = evaluate_correlation_cluster_gate(
        preregistration,
        correlation_matrix,
        selection_cells,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    complete_link_audit = build_correlation_cluster_complete_link_audit(
        preregistration,
        correlation_matrix,
    )
    legacy_passed = legacy_gate.get("status") == "PASS"
    topology_passed = complete_link_audit.get("status") == "PASS"
    blockers = []
    if not legacy_passed:
        blockers.append("legacy_cluster_gate_blocked")
    if not topology_passed:
        blockers.append("cluster_complete_link_audit_blocked")
    first_blocking_tier = (
        None
        if not blockers
        else "LEGACY_GATE"
        if not legacy_passed
        else "CLUSTER_COMPLETE_LINK"
    )
    payload = {
        "schema_version": GATE_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "strategy_id": strategy_id,
        "variant_id": variant_id,
        "lane": lane,
        "first_blocking_tier": first_blocking_tier,
        "tiers": [
            {
                "tier_id": "LEGACY_GATE",
                "status": "PASS" if legacy_passed else "BLOCK",
                "blockers": [] if legacy_passed else ["legacy_cluster_gate_blocked"],
            },
            {
                "tier_id": "CLUSTER_COMPLETE_LINK",
                "status": "PASS" if topology_passed else "BLOCK",
                "blockers": (
                    []
                    if topology_passed
                    else ["cluster_complete_link_audit_blocked"]
                ),
            },
        ],
        "blockers": blockers,
        "legacy_gate": legacy_gate,
        "complete_link_audit": complete_link_audit,
        "requires_new_report_schema": True,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return _seal(payload, "gate_hash")


def verify_correlation_cluster_gate_v2(
    document: Any,
    *,
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    try:
        expected = evaluate_correlation_cluster_gate_v2(
            preregistration,
            correlation_matrix,
            selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (KeyError, TypeError, ValueError):
        return _verification(
            GATE_VERIFICATION_SCHEMA_VERSION,
            ["correlation_cluster_gate_v2_source_invalid"],
        )
    blockers = (
        []
        if type(document) is dict
        and strict_json_contract_equal(document, expected)
        else [
        "correlation_cluster_gate_v2_contract_invalid"
        ]
    )
    return _verification(GATE_VERIFICATION_SCHEMA_VERSION, blockers)
