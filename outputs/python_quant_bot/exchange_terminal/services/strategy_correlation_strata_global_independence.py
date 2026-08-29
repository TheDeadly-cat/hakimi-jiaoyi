"""Cross-dimension global independence gate for preregistered strata."""

from __future__ import annotations

import math
from typing import Any

try:
    from services.strategy_correlation_preregistered_strata import (
        verify_strategy_correlation_strata_gate,
        verify_strategy_correlation_strata_preregistration,
    )
    from services.strict_canonical_json_hash import strict_canonical_hash
    from services.strict_research_authority import (
        strict_research_authority_invalid,
    )
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_preregistered_strata import (
        verify_strategy_correlation_strata_gate,
        verify_strategy_correlation_strata_preregistration,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_canonical_hash,
    )
    from exchange_terminal.services.strict_research_authority import (
        strict_research_authority_invalid,
    )


AUDIT_SCHEMA_VERSION = (
    "strategy-correlation-strata-global-independence-audit-v1"
)
GATE_SCHEMA_VERSION = "strategy-correlation-preregistered-strata-gate-v2"
MINIMUM_GLOBAL_INDEPENDENT_VOTES = 2
REQUIRED_GLOBAL_INDEPENDENT_FRACTION = 0.60
MAX_EXACT_CLUSTER_COUNT = 24
MAX_SEARCH_NODES = 250_000


def _hash_without(document: dict[str, Any], hash_field: str) -> str:
    return strict_canonical_hash(
        {key: value for key, value in document.items() if key != hash_field}
    )


def _maximum_independent_set(
    nodes: list[str],
    adjacency: dict[str, set[str]],
) -> tuple[list[str], int]:
    ordered_nodes = tuple(sorted(nodes))
    best: tuple[str, ...] = ()
    search_nodes = 0

    def search(
        candidates: tuple[str, ...],
        chosen: tuple[str, ...],
    ) -> None:
        nonlocal best, search_nodes
        search_nodes += 1
        if search_nodes > MAX_SEARCH_NODES:
            raise ValueError("global_independence_search_limit_exceeded")
        if len(chosen) + len(candidates) <= len(best):
            return
        if not candidates:
            best = tuple(sorted(chosen))
            return
        candidate_set = set(candidates)
        max_degree = max(
            len(adjacency[node] & candidate_set) for node in candidates
        )
        vertex = next(
            node
            for node in candidates
            if len(adjacency[node] & candidate_set) == max_degree
        )
        included_candidates = tuple(
            node
            for node in candidates
            if node != vertex and node not in adjacency[vertex]
        )
        search(included_candidates, chosen + (vertex,))
        excluded_candidates = tuple(
            node for node in candidates if node != vertex
        )
        search(excluded_candidates, chosen)

    search(ordered_nodes, ())
    return list(best), search_nodes


def _validated_cluster_statuses(
    registration: dict[str, Any],
    complete_link_gate: Any,
) -> dict[str, str]:
    if type(complete_link_gate) is not dict:
        raise ValueError("complete_link_gate_invalid")
    legacy_gate = complete_link_gate.get("legacy_gate")
    if type(legacy_gate) is not dict:
        raise ValueError("complete_link_legacy_gate_invalid")
    cluster_results = legacy_gate.get("cluster_results")
    if type(cluster_results) is not list:
        raise ValueError("complete_link_cluster_results_invalid")
    statuses: dict[str, str] = {}
    for result in cluster_results:
        if type(result) is not dict:
            raise ValueError("complete_link_cluster_result_invalid")
        cluster_id = result.get("cluster_id")
        status = result.get("status")
        if (
            type(cluster_id) is not str
            or not cluster_id
            or cluster_id in statuses
            or status not in {"PASS", "BLOCK"}
        ):
            raise ValueError("complete_link_cluster_result_invalid")
        statuses[cluster_id] = status
    if set(statuses) != set(registration.get("cluster_ids", [])):
        raise ValueError("complete_link_cluster_coverage_invalid")
    return statuses


def _conflict_graph(
    registration: dict[str, Any],
) -> tuple[dict[str, set[str]], list[dict[str, Any]]]:
    cluster_ids = sorted(registration["cluster_ids"])
    shared_dimensions: dict[tuple[str, str], list[str]] = {}
    for dimension in registration["dimensions"]:
        dimension_id = dimension["dimension_id"]
        for stratum in dimension["strata"]:
            members = sorted(stratum["cluster_ids"])
            for left_index, left in enumerate(members):
                for right in members[left_index + 1 :]:
                    shared_dimensions.setdefault((left, right), []).append(
                        dimension_id
                    )
    adjacency = {cluster_id: set() for cluster_id in cluster_ids}
    conflict_pairs: list[dict[str, Any]] = []
    for (left, right), dimensions in sorted(shared_dimensions.items()):
        adjacency[left].add(right)
        adjacency[right].add(left)
        conflict_pairs.append(
            {
                "left_cluster_id": left,
                "right_cluster_id": right,
                "shared_dimension_ids": sorted(dimensions),
            }
        )
    return adjacency, conflict_pairs


def _build_global_independence_audit(
    registration: dict[str, Any],
    complete_link_gate: dict[str, Any],
) -> dict[str, Any]:
    cluster_ids = sorted(registration["cluster_ids"])
    statuses = _validated_cluster_statuses(
        registration,
        complete_link_gate,
    )
    adjacency, conflict_pairs = _conflict_graph(registration)
    blockers: list[str] = []
    registered_witness: list[str] = []
    passing_witness: list[str] = []
    registered_capacity = None
    passing_capacity = None
    search_node_count = 0
    if len(cluster_ids) > MAX_EXACT_CLUSTER_COUNT:
        blockers.append("global_independence_cluster_limit_exceeded")
    else:
        try:
            registered_witness, registered_nodes = (
                _maximum_independent_set(cluster_ids, adjacency)
            )
            passing_ids = [
                cluster_id
                for cluster_id in cluster_ids
                if statuses[cluster_id] == "PASS"
            ]
            passing_witness, passing_nodes = _maximum_independent_set(
                passing_ids,
                adjacency,
            )
            search_node_count = registered_nodes + passing_nodes
            registered_capacity = len(registered_witness)
            passing_capacity = len(passing_witness)
        except ValueError:
            blockers.append("global_independence_search_limit_exceeded")
    required_votes = (
        max(
            MINIMUM_GLOBAL_INDEPENDENT_VOTES,
            math.ceil(
                registered_capacity
                * REQUIRED_GLOBAL_INDEPENDENT_FRACTION
            ),
        )
        if registered_capacity is not None
        else None
    )
    document: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "strata_registration_hash": registration["registration_hash"],
        "complete_link_gate_hash": complete_link_gate["gate_hash"],
        "cluster_count": len(cluster_ids),
        "passing_cluster_count": sum(
            status == "PASS" for status in statuses.values()
        ),
        "conflict_pair_count": len(conflict_pairs),
        "conflict_pairs": conflict_pairs,
        "registered_independent_capacity": registered_capacity,
        "passing_independent_capacity": passing_capacity,
        "registered_independent_witness": registered_witness,
        "passing_independent_witness": passing_witness,
        "minimum_global_independent_votes": (
            MINIMUM_GLOBAL_INDEPENDENT_VOTES
        ),
        "required_global_independent_fraction": (
            REQUIRED_GLOBAL_INDEPENDENT_FRACTION
        ),
        "required_global_independent_votes": required_votes,
        "exact_search_cluster_limit": MAX_EXACT_CLUSTER_COUNT,
        "exact_search_node_limit": MAX_SEARCH_NODES,
        "search_node_count": search_node_count,
        "consumer_only": True,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "requires_new_report_schema": True,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    document["audit_hash"] = _hash_without(document, "audit_hash")
    return document


def evaluate_strategy_correlation_strata_global_independence_gate(
    registration: Any,
    complete_link_gate: Any,
    strata_gate: Any,
    *,
    source_preregistration: Any,
) -> dict[str, Any]:
    registration_verification = (
        verify_strategy_correlation_strata_preregistration(
            registration,
            source_preregistration=source_preregistration,
        )
    )
    if registration_verification.get("status") != "PASS":
        raise ValueError("strata_registration_independent_verification_failed")
    strata_gate_verification = verify_strategy_correlation_strata_gate(
        strata_gate,
        registration=registration,
        complete_link_gate=complete_link_gate,
        source_preregistration=source_preregistration,
    )
    if strata_gate_verification.get("status") != "PASS":
        raise ValueError("base_strata_gate_independent_verification_failed")
    if (
        type(registration) is not dict
        or type(complete_link_gate) is not dict
        or type(strata_gate) is not dict
        or strict_research_authority_invalid(registration)
        or strict_research_authority_invalid(complete_link_gate)
        or strict_research_authority_invalid(strata_gate)
    ):
        raise ValueError("global_independence_source_authority_invalid")
    audit = _build_global_independence_audit(
        registration,
        complete_link_gate,
    )
    blockers: list[str] = []
    if strata_gate.get("status") != "PASS":
        blockers.append("base_strata_gate_blocked")
    if audit["status"] != "PASS":
        blockers.append("global_independence_audit_blocked")
    elif (
        audit["passing_independent_capacity"]
        < audit["required_global_independent_votes"]
    ):
        blockers.append("minimum_global_independent_votes_not_met")
    first_blocking_tier = None
    if strata_gate.get("status") != "PASS":
        first_blocking_tier = "BASE_STRATA_GATE"
    elif audit["status"] != "PASS":
        first_blocking_tier = "GLOBAL_INDEPENDENCE_AUDIT"
    elif blockers:
        first_blocking_tier = "GLOBAL_INDEPENDENCE_VOTE"
    document: dict[str, Any] = {
        "schema_version": GATE_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "first_blocking_tier": first_blocking_tier,
        "strategy_id": strata_gate.get("strategy_id"),
        "variant_id": strata_gate.get("variant_id"),
        "lane": strata_gate.get("lane"),
        "strata_registration_hash": registration["registration_hash"],
        "base_strata_gate_hash": strata_gate["gate_hash"],
        "global_independence_audit": audit,
        "consumer_only": True,
        "writer_implemented": False,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "requires_new_report_schema": True,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        "tiers": [
            {
                "tier_id": "BASE_STRATA_GATE",
                "status": strata_gate.get("status"),
            },
            {
                "tier_id": "GLOBAL_INDEPENDENCE_AUDIT",
                "status": audit["status"],
            },
            {
                "tier_id": "GLOBAL_INDEPENDENCE_VOTE",
                "status": (
                    "PASS"
                    if audit["status"] == "PASS"
                    and audit["passing_independent_capacity"]
                    >= audit["required_global_independent_votes"]
                    else "BLOCK"
                ),
            },
        ],
    }
    document["gate_hash"] = _hash_without(document, "gate_hash")
    return document


def verify_strategy_correlation_strata_global_independence_gate(
    document: Any,
    *,
    registration: Any,
    complete_link_gate: Any,
    strata_gate: Any,
    source_preregistration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return {
            "status": "BLOCK",
            "blockers": ["global_independence_gate_contract_invalid"],
        }
    if strict_research_authority_invalid(document):
        blockers.append("global_independence_gate_authority_invalid")
    try:
        if document.get("gate_hash") != _hash_without(
            document,
            "gate_hash",
        ):
            blockers.append("global_independence_gate_hash_invalid")
    except (TypeError, ValueError):
        blockers.append("global_independence_gate_hash_invalid")
    try:
        expected = (
            evaluate_strategy_correlation_strata_global_independence_gate(
                registration,
                complete_link_gate,
                strata_gate,
                source_preregistration=source_preregistration,
            )
        )
    except (MemoryError, RecursionError):
        raise
    except (KeyError, TypeError, ValueError):
        blockers.append("global_independence_gate_rebuild_invalid")
    else:
        if document != expected:
            blockers.append("global_independence_gate_exact_rebuild_mismatch")
    blockers = sorted(set(blockers))
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
    }
