"""Consumer-first gate for preregistered correlation strata.

The complete-link gate prevents weak internal topology inside a cluster.  This
module adds a separate, ex-ante hierarchy: clusters sharing an asset family,
sector, region, or common risk factor cannot silently become independent votes.
It does not implement a report writer or activate a current pointer.
"""

from __future__ import annotations

import math
from typing import Any

try:
    from services.strategy_correlation_cluster_gate import (
        verify_correlation_cluster_preregistration,
    )
    from services.strict_research_authority import (
        strict_research_authority_invalid,
    )
    from services.strict_canonical_json_hash import strict_canonical_hash
except ModuleNotFoundError:
    from exchange_terminal.services.strategy_correlation_cluster_gate import (
        verify_correlation_cluster_preregistration,
    )
    from exchange_terminal.services.strict_research_authority import (
        strict_research_authority_invalid,
    )
    from exchange_terminal.services.strict_canonical_json_hash import (
        strict_canonical_hash,
    )


REGISTRATION_SCHEMA = "strategy-correlation-preregistered-strata-registration-v1"
GATE_SCHEMA = "strategy-correlation-preregistered-strata-gate-v1"
SOURCE_PREREGISTRATION_SCHEMA = "strategy-correlation-cluster-preregistration-v1"
SOURCE_GATE_SCHEMA = "strategy-correlation-cluster-gate-v2"
MINIMUM_INDEPENDENT_STRATA = 2
REQUIRED_STRATA_FRACTION = 0.60
MAXIMUM_VOTES_PER_STRATUM = 1
STRATUM_VOTE_RULE = "ALL_MEMBER_CLUSTERS_PASS"


def _verification(blockers: list[str]) -> dict[str, Any]:
    normalized = sorted(set(blockers))
    return {
        "status": "PASS" if not normalized else "BLOCK",
        "blockers": normalized,
    }


def _clean_identifier(value: Any, *, field: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{field}_invalid")
    return value


def _hash_without(document: dict[str, Any], hash_field: str) -> str:
    return strict_canonical_hash(
        {key: value for key, value in document.items() if key != hash_field}
    )


def _source_cluster_ids(preregistration: Any) -> list[str]:
    if type(preregistration) is not dict:
        raise ValueError("source_preregistration_invalid")
    if preregistration.get("schema_version") != SOURCE_PREREGISTRATION_SCHEMA:
        raise ValueError("source_preregistration_schema_invalid")
    if strict_research_authority_invalid(preregistration):
        raise ValueError("source_preregistration_authority_invalid")
    verification = verify_correlation_cluster_preregistration(preregistration)
    if verification.get("status") != "PASS":
        raise ValueError("source_preregistration_invalid")
    clusters = preregistration.get("clusters")
    if type(clusters) is not list or not clusters:
        raise ValueError("source_preregistration_clusters_invalid")
    cluster_ids = [
        _clean_identifier(cluster.get("cluster_id"), field="cluster_id")
        for cluster in clusters
        if type(cluster) is dict
    ]
    if len(cluster_ids) != len(clusters) or len(set(cluster_ids)) != len(cluster_ids):
        raise ValueError("source_preregistration_clusters_invalid")
    return sorted(cluster_ids)


def _normalize_dimensions(
    dimensions: Any,
    *,
    expected_cluster_ids: list[str],
) -> list[dict[str, Any]]:
    if type(dimensions) is not list or not dimensions:
        raise ValueError("strata_dimensions_invalid")
    expected = set(expected_cluster_ids)
    dimension_ids: set[str] = set()
    normalized_dimensions: list[dict[str, Any]] = []
    for dimension in dimensions:
        if type(dimension) is not dict or set(dimension) != {
            "dimension_id",
            "strata",
        }:
            raise ValueError("strata_dimension_contract_invalid")
        dimension_id = _clean_identifier(
            dimension.get("dimension_id"),
            field="dimension_id",
        )
        if dimension_id in dimension_ids:
            raise ValueError("strata_dimension_id_duplicate")
        dimension_ids.add(dimension_id)
        strata = dimension.get("strata")
        if type(strata) is not list or not strata:
            raise ValueError("strata_dimension_empty")
        stratum_ids: set[str] = set()
        assigned: list[str] = []
        normalized_strata: list[dict[str, Any]] = []
        for stratum in strata:
            if type(stratum) is not dict or set(stratum) != {
                "stratum_id",
                "cluster_ids",
            }:
                raise ValueError("stratum_contract_invalid")
            stratum_id = _clean_identifier(
                stratum.get("stratum_id"),
                field="stratum_id",
            )
            if stratum_id in stratum_ids:
                raise ValueError("stratum_id_duplicate")
            stratum_ids.add(stratum_id)
            cluster_ids = stratum.get("cluster_ids")
            if type(cluster_ids) is not list or not cluster_ids:
                raise ValueError("stratum_cluster_ids_invalid")
            normalized_cluster_ids = [
                _clean_identifier(value, field="stratum_cluster_id")
                for value in cluster_ids
            ]
            if len(set(normalized_cluster_ids)) != len(normalized_cluster_ids):
                raise ValueError("stratum_cluster_id_duplicate")
            if not set(normalized_cluster_ids).issubset(expected):
                raise ValueError("stratum_cluster_id_unknown")
            assigned.extend(normalized_cluster_ids)
            normalized_strata.append(
                {
                    "stratum_id": stratum_id,
                    "cluster_ids": sorted(normalized_cluster_ids),
                }
            )
        if len(assigned) != len(set(assigned)) or set(assigned) != expected:
            raise ValueError("strata_dimension_cluster_partition_invalid")
        normalized_dimensions.append(
            {
                "dimension_id": dimension_id,
                "strata": sorted(
                    normalized_strata,
                    key=lambda value: value["stratum_id"],
                ),
            }
        )
    return sorted(normalized_dimensions, key=lambda value: value["dimension_id"])


def build_strategy_correlation_strata_preregistration(
    source_preregistration: Any,
    dimensions: Any,
) -> dict[str, Any]:
    cluster_ids = _source_cluster_ids(source_preregistration)
    normalized_dimensions = _normalize_dimensions(
        dimensions,
        expected_cluster_ids=cluster_ids,
    )
    source_hash = _clean_identifier(
        source_preregistration.get("preregistration_hash"),
        field="source_preregistration_hash",
    )
    document: dict[str, Any] = {
        "schema_version": REGISTRATION_SCHEMA,
        "status": "PREREGISTERED",
        "source_preregistration_schema": SOURCE_PREREGISTRATION_SCHEMA,
        "source_preregistration_hash": source_hash,
        "cluster_ids": cluster_ids,
        "dimensions": normalized_dimensions,
        "minimum_independent_strata": MINIMUM_INDEPENDENT_STRATA,
        "required_strata_fraction": REQUIRED_STRATA_FRACTION,
        "maximum_votes_per_stratum": MAXIMUM_VOTES_PER_STRATUM,
        "stratum_vote_rule": STRATUM_VOTE_RULE,
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
    document["registration_hash"] = _hash_without(document, "registration_hash")
    return document


def verify_strategy_correlation_strata_preregistration(
    document: Any,
    *,
    source_preregistration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["strata_registration_contract_invalid"])
    if strict_research_authority_invalid(document):
        blockers.append("strata_registration_authority_invalid")
    stored_hash = document.get("registration_hash")
    if type(stored_hash) is not str or stored_hash != _hash_without(
        document,
        "registration_hash",
    ):
        blockers.append("strata_registration_hash_invalid")
    try:
        expected = build_strategy_correlation_strata_preregistration(
            source_preregistration,
            document.get("dimensions"),
        )
    except (MemoryError, RecursionError):
        raise
    except (TypeError, ValueError):
        blockers.append("strata_registration_rebuild_invalid")
    else:
        if document != expected:
            blockers.append("strata_registration_exact_rebuild_mismatch")
    return _verification(blockers)


def _validated_cluster_statuses(
    complete_link_gate: Any,
    *,
    registration: dict[str, Any],
) -> tuple[dict[str, str], str]:
    if type(complete_link_gate) is not dict:
        raise ValueError("complete_link_gate_invalid")
    if complete_link_gate.get("schema_version") != SOURCE_GATE_SCHEMA:
        raise ValueError("complete_link_gate_schema_invalid")
    if strict_research_authority_invalid(complete_link_gate):
        raise ValueError("complete_link_gate_authority_invalid")
    stored_hash = complete_link_gate.get("gate_hash")
    if type(stored_hash) is not str or stored_hash != _hash_without(
        complete_link_gate,
        "gate_hash",
    ):
        raise ValueError("complete_link_gate_hash_invalid")
    gate_status = complete_link_gate.get("status")
    if gate_status not in {"PASS", "BLOCK"}:
        raise ValueError("complete_link_gate_status_invalid")
    legacy_gate = complete_link_gate.get("legacy_gate")
    if type(legacy_gate) is not dict:
        raise ValueError("complete_link_legacy_gate_invalid")
    if (
        legacy_gate.get("preregistration_hash")
        != registration.get("source_preregistration_hash")
    ):
        raise ValueError("complete_link_preregistration_binding_invalid")
    cluster_results = legacy_gate.get("cluster_results")
    if type(cluster_results) is not list:
        raise ValueError("complete_link_cluster_results_invalid")
    statuses: dict[str, str] = {}
    for result in cluster_results:
        if type(result) is not dict:
            raise ValueError("complete_link_cluster_result_invalid")
        cluster_id = _clean_identifier(
            result.get("cluster_id"),
            field="complete_link_cluster_id",
        )
        status = result.get("status")
        if cluster_id in statuses or status not in {"PASS", "BLOCK"}:
            raise ValueError("complete_link_cluster_result_invalid")
        statuses[cluster_id] = status
    if set(statuses) != set(registration.get("cluster_ids", [])):
        raise ValueError("complete_link_cluster_coverage_invalid")
    return statuses, gate_status


def evaluate_strategy_correlation_strata_gate(
    registration: Any,
    complete_link_gate: Any,
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
        raise ValueError(
            "strata_registration_independent_verification_failed"
        )
    if type(registration) is not dict:
        raise ValueError("strata_registration_invalid")
    if strict_research_authority_invalid(registration):
        raise ValueError("strata_registration_authority_invalid")
    if registration.get("schema_version") != REGISTRATION_SCHEMA:
        raise ValueError("strata_registration_schema_invalid")
    stored_registration_hash = registration.get("registration_hash")
    if (
        type(stored_registration_hash) is not str
        or stored_registration_hash
        != _hash_without(registration, "registration_hash")
    ):
        raise ValueError("strata_registration_hash_invalid")
    cluster_statuses, base_gate_status = _validated_cluster_statuses(
        complete_link_gate,
        registration=registration,
    )
    dimension_results: list[dict[str, Any]] = []
    blocked_dimensions: list[str] = []
    for dimension in registration.get("dimensions", []):
        stratum_results: list[dict[str, Any]] = []
        for stratum in dimension["strata"]:
            member_results = [
                {
                    "cluster_id": cluster_id,
                    "status": cluster_statuses[cluster_id],
                }
                for cluster_id in stratum["cluster_ids"]
            ]
            status = (
                "PASS"
                if all(result["status"] == "PASS" for result in member_results)
                else "BLOCK"
            )
            stratum_results.append(
                {
                    "stratum_id": stratum["stratum_id"],
                    "member_cluster_results": member_results,
                    "status": status,
                    "vote_count": 1 if status == "PASS" else 0,
                }
            )
        passing_count = sum(
            result["vote_count"] for result in stratum_results
        )
        fractional_requirement = math.ceil(
            len(stratum_results) * REQUIRED_STRATA_FRACTION
        )
        required_votes = max(
            MINIMUM_INDEPENDENT_STRATA,
            fractional_requirement,
        )
        blockers: list[str] = []
        if passing_count < MINIMUM_INDEPENDENT_STRATA:
            blockers.append("minimum_independent_strata_not_met")
        if passing_count < fractional_requirement:
            blockers.append("required_strata_fraction_not_met")
        dimension_status = "PASS" if not blockers else "BLOCK"
        if dimension_status == "BLOCK":
            blocked_dimensions.append(dimension["dimension_id"])
        dimension_results.append(
            {
                "dimension_id": dimension["dimension_id"],
                "stratum_results": stratum_results,
                "passing_stratum_count": passing_count,
                "total_stratum_count": len(stratum_results),
                "required_stratum_votes": required_votes,
                "blockers": blockers,
                "status": dimension_status,
            }
        )
    blockers: list[str] = []
    if base_gate_status != "PASS":
        blockers.append("base_complete_link_gate_blocked")
    blockers.extend(
        f"strata_dimension_blocked:{dimension_id}"
        for dimension_id in blocked_dimensions
    )
    status = "PASS" if not blockers else "BLOCK"
    first_blocking_tier = None
    if base_gate_status != "PASS":
        first_blocking_tier = "BASE_COMPLETE_LINK"
    elif blocked_dimensions:
        first_blocking_tier = "PREREGISTERED_STRATA"
    document: dict[str, Any] = {
        "schema_version": GATE_SCHEMA,
        "status": status,
        "blockers": blockers,
        "first_blocking_tier": first_blocking_tier,
        "strategy_id": complete_link_gate.get("strategy_id"),
        "variant_id": complete_link_gate.get("variant_id"),
        "lane": complete_link_gate.get("lane"),
        "source_preregistration_hash": registration[
            "source_preregistration_hash"
        ],
        "strata_registration_hash": registration["registration_hash"],
        "base_complete_link_gate_hash": complete_link_gate["gate_hash"],
        "base_complete_link_gate_status": base_gate_status,
        "source_preregistration_independently_verified": True,
        "dimension_results": dimension_results,
        "minimum_independent_strata": MINIMUM_INDEPENDENT_STRATA,
        "required_strata_fraction": REQUIRED_STRATA_FRACTION,
        "maximum_votes_per_stratum": MAXIMUM_VOTES_PER_STRATUM,
        "stratum_vote_rule": STRATUM_VOTE_RULE,
        "base_gate_independent_verification_required": True,
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
                "tier_id": "BASE_COMPLETE_LINK",
                "status": base_gate_status,
            },
            {
                "tier_id": "PREREGISTERED_STRATA",
                "status": "PASS" if not blocked_dimensions else "BLOCK",
            },
        ],
    }
    document["gate_hash"] = _hash_without(document, "gate_hash")
    return document


def verify_strategy_correlation_strata_gate(
    document: Any,
    *,
    registration: Any,
    complete_link_gate: Any,
    source_preregistration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["strata_gate_contract_invalid"])
    if strict_research_authority_invalid(document):
        blockers.append("strata_gate_authority_invalid")
    stored_hash = document.get("gate_hash")
    if type(stored_hash) is not str or stored_hash != _hash_without(
        document,
        "gate_hash",
    ):
        blockers.append("strata_gate_hash_invalid")
    try:
        expected = evaluate_strategy_correlation_strata_gate(
            registration,
            complete_link_gate,
            source_preregistration=source_preregistration,
        )
    except (MemoryError, RecursionError):
        raise
    except (TypeError, ValueError):
        blockers.append("strata_gate_rebuild_invalid")
    else:
        if document != expected:
            blockers.append("strata_gate_exact_rebuild_mismatch")
    return _verification(blockers)
