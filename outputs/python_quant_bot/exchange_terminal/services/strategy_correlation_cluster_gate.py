from __future__ import annotations

import hashlib
import json
import math
from itertools import combinations
from typing import Any

from .execution_authority import authority_violations


PREREGISTRATION_SCHEMA_VERSION = "strategy-correlation-cluster-preregistration-v1"
CORRELATION_MATRIX_SCHEMA_VERSION = "strategy-selection-correlation-matrix-v1"
GATE_SCHEMA_VERSION = "strategy-correlation-cluster-gate-v1"
RETURN_SERIES = "COMPLETED_DAILY_RETURNS"
ABSOLUTE_PEARSON_THRESHOLD = 0.75
LOOKBACK_OBSERVATIONS = 60
MINIMUM_PAIR_OVERLAP = 40
MINIMUM_INDEPENDENT_CLUSTERS = 2
REQUIRED_CLUSTER_FRACTION = 0.60
LANES = frozenset({"RAW_EXCESS", "RISK_ADJUSTED"})

_PERMISSIONS = {
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_finite_number(value: Any) -> bool:
    return type(value) in {int, float} and math.isfinite(float(value))


def _clean_symbol(value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError("symbols must be non-empty strings")
    return value.strip().upper()


def _clean_identity(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a trimmed non-empty string")
    return value


def _authority_invalid(value: Any) -> bool:
    try:
        return bool(authority_violations(value))
    except (MemoryError, RecursionError, TypeError, ValueError):
        return True


def _verification(blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "BLOCK" if blockers else "PASS",
        "blockers": sorted(set(blockers)),
    }


def build_correlation_cluster_preregistration(
    clusters: list[dict[str, Any]],
) -> dict[str, Any]:
    if type(clusters) is not list or not clusters:
        raise ValueError("clusters must be a non-empty list")

    normalized_clusters: list[dict[str, Any]] = []
    seen_cluster_ids: set[str] = set()
    seen_symbols: set[str] = set()
    for cluster in clusters:
        if type(cluster) is not dict or set(cluster) != {"cluster_id", "members"}:
            raise ValueError("each cluster must contain exactly cluster_id and members")
        cluster_id = _clean_identity(cluster["cluster_id"], "cluster_id")
        cluster_key = cluster_id.casefold()
        if cluster_key in seen_cluster_ids:
            raise ValueError("cluster_id values must be unique")
        seen_cluster_ids.add(cluster_key)
        members = cluster["members"]
        if type(members) is not list or not members:
            raise ValueError("cluster members must be a non-empty list")
        clean_members = sorted(_clean_symbol(member) for member in members)
        if len(set(clean_members)) != len(clean_members):
            raise ValueError("cluster members must be unique")
        overlap = seen_symbols.intersection(clean_members)
        if overlap:
            raise ValueError("each symbol must belong to exactly one cluster")
        seen_symbols.update(clean_members)
        normalized_clusters.append({"cluster_id": cluster_id, "members": clean_members})

    normalized_clusters.sort(key=lambda item: item["cluster_id"].casefold())
    body = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "return_series": RETURN_SERIES,
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "lookback_observations": LOOKBACK_OBSERVATIONS,
        "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
        "minimum_independent_clusters": MINIMUM_INDEPENDENT_CLUSTERS,
        "cluster_vote_rule": "ALL_MEMBERS_PASS",
        "maximum_votes_per_cluster": 1,
        "required_cluster_fraction": REQUIRED_CLUSTER_FRACTION,
        "symbols": sorted(seen_symbols),
        "clusters": normalized_clusters,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_new_report_schema": True,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "preregistration_hash": _sha256(body)}


def verify_correlation_cluster_preregistration(document: Any) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["preregistration_contract_invalid"])
    if _authority_invalid(document):
        blockers.append("execution_authority_invalid")
    expected_keys = {
        "schema_version",
        "return_series",
        "absolute_pearson_threshold",
        "lookback_observations",
        "minimum_pair_overlap",
        "minimum_independent_clusters",
        "cluster_vote_rule",
        "maximum_votes_per_cluster",
        "required_cluster_fraction",
        "symbols",
        "clusters",
        "current_writer_activation_allowed",
        "current_admission_allowed",
        "requires_new_report_schema",
        "permissions",
        "preregistration_hash",
    }
    if set(document) != expected_keys:
        blockers.append("preregistration_contract_invalid")
        return _verification(blockers)
    try:
        rebuilt = build_correlation_cluster_preregistration(document["clusters"])
    except (MemoryError, TypeError, ValueError):
        blockers.append("preregistration_contract_invalid")
        return _verification(blockers)
    if document != rebuilt:
        blockers.append("preregistration_contract_invalid")
    return _verification(blockers)


def _normalize_pair_mapping(values: dict[Any, Any]) -> dict[tuple[str, str], Any]:
    if type(values) is not dict:
        raise ValueError("pair values must be a dictionary")
    normalized: dict[tuple[str, str], Any] = {}
    for raw_pair, value in values.items():
        if type(raw_pair) is not tuple or len(raw_pair) != 2:
            raise ValueError("pair keys must be two-item tuples")
        left, right = sorted((_clean_symbol(raw_pair[0]), _clean_symbol(raw_pair[1])))
        if left == right or (left, right) in normalized:
            raise ValueError("pair keys must be unique distinct symbols")
        normalized[(left, right)] = value
    return normalized


def build_correlation_matrix_contract(
    symbols: list[str],
    correlations: dict[tuple[str, str], float],
    *,
    overlap_observations: int | dict[tuple[str, str], int] = LOOKBACK_OBSERVATIONS,
) -> dict[str, Any]:
    if type(symbols) is not list:
        raise ValueError("symbols must be a list")
    clean_symbols = sorted(_clean_symbol(symbol) for symbol in symbols)
    if len(clean_symbols) < 2 or len(set(clean_symbols)) != len(clean_symbols):
        raise ValueError("matrix symbols must be unique and contain at least two symbols")
    normalized_correlations = _normalize_pair_mapping(correlations)
    expected_pairs = set(combinations(clean_symbols, 2))
    if set(normalized_correlations) != expected_pairs:
        raise ValueError("correlations must cover every symbol pair exactly once")
    if type(overlap_observations) is dict:
        normalized_overlaps = _normalize_pair_mapping(overlap_observations)
        if set(normalized_overlaps) != expected_pairs:
            raise ValueError("overlap values must cover every symbol pair exactly once")
    else:
        normalized_overlaps = {pair: overlap_observations for pair in expected_pairs}

    pairs: list[dict[str, Any]] = []
    for left, right in sorted(expected_pairs):
        correlation = normalized_correlations[(left, right)]
        overlap = normalized_overlaps[(left, right)]
        if not _is_finite_number(correlation) or not -1 <= float(correlation) <= 1:
            raise ValueError("correlations must be finite values from -1 through 1")
        if type(overlap) is not int or overlap < 0:
            raise ValueError("overlap observations must be non-negative native integers")
        pairs.append({
            "left_symbol": left,
            "right_symbol": right,
            "overlap_observations": overlap,
            "pearson_correlation": float(correlation),
        })

    body = {
        "schema_version": CORRELATION_MATRIX_SCHEMA_VERSION,
        "status": "PASS",
        "return_series": RETURN_SERIES,
        "lookback_observations": LOOKBACK_OBSERVATIONS,
        "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
        "symbols": clean_symbols,
        "pairs": pairs,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "matrix_hash": _sha256(body)}


def verify_correlation_matrix_contract(
    document: Any,
    *,
    expected_symbols: list[str],
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["correlation_matrix_contract_invalid"])
    if _authority_invalid(document):
        blockers.append("execution_authority_invalid")
    expected_keys = {
        "schema_version",
        "status",
        "return_series",
        "lookback_observations",
        "minimum_pair_overlap",
        "symbols",
        "pairs",
        "permissions",
        "matrix_hash",
    }
    if set(document) != expected_keys:
        blockers.append("correlation_matrix_contract_invalid")
        return _verification(blockers)
    try:
        clean_expected = sorted(_clean_symbol(symbol) for symbol in expected_symbols)
    except (MemoryError, TypeError, ValueError):
        blockers.append("correlation_matrix_contract_invalid")
        return _verification(blockers)
    if (
        document["schema_version"] != CORRELATION_MATRIX_SCHEMA_VERSION
        or document["status"] != "PASS"
        or document["return_series"] != RETURN_SERIES
        or document["lookback_observations"] != LOOKBACK_OBSERVATIONS
        or document["minimum_pair_overlap"] != MINIMUM_PAIR_OVERLAP
        or document["symbols"] != clean_expected
        or document["permissions"] != _PERMISSIONS
    ):
        blockers.append("correlation_matrix_contract_invalid")
    pairs = document["pairs"]
    expected_pairs = set(combinations(clean_expected, 2))
    observed_pairs: list[tuple[str, str]] = []
    if type(pairs) is not list:
        blockers.append("correlation_matrix_contract_invalid")
    else:
        for pair in pairs:
            if type(pair) is not dict or set(pair) != {
                "left_symbol",
                "right_symbol",
                "overlap_observations",
                "pearson_correlation",
            }:
                blockers.append("correlation_matrix_contract_invalid")
                continue
            left = pair["left_symbol"]
            right = pair["right_symbol"]
            correlation = pair["pearson_correlation"]
            overlap = pair["overlap_observations"]
            if (
                type(left) is not str
                or type(right) is not str
                or left >= right
                or type(overlap) is not int
                or overlap < 0
                or not _is_finite_number(correlation)
                or not -1 <= float(correlation) <= 1
            ):
                blockers.append("correlation_matrix_contract_invalid")
                continue
            observed_pairs.append((left, right))
        if observed_pairs != sorted(expected_pairs):
            blockers.append("correlation_matrix_contract_invalid")
    body = {key: value for key, value in document.items() if key != "matrix_hash"}
    try:
        if type(document["matrix_hash"]) is not str or document["matrix_hash"] != _sha256(body):
            blockers.append("correlation_matrix_contract_invalid")
    except (MemoryError, TypeError, ValueError):
        blockers.append("correlation_matrix_contract_invalid")
    return _verification(blockers)


def _selection_outcomes(
    cells: Any,
    *,
    strategy_id: str,
    variant_id: str,
    lane: str,
    expected_symbols: list[str],
) -> tuple[dict[str, str], list[str]]:
    blockers: list[str] = []
    outcomes: dict[str, str] = {}
    if type(cells) is not list:
        return outcomes, ["selection_cell_contract_invalid"]
    for cell in cells:
        if type(cell) is not dict or set(cell) != {
            "strategy_id", "variant_id", "symbol", "lane", "gate_status"
        }:
            blockers.append("selection_cell_contract_invalid")
            continue
        if _authority_invalid(cell):
            blockers.append("execution_authority_invalid")
        if (
            type(cell["strategy_id"]) is not str
            or type(cell["variant_id"]) is not str
            or type(cell["symbol"]) is not str
            or type(cell["lane"]) is not str
            or cell["lane"] not in LANES
            or type(cell["gate_status"]) is not str
            or cell["gate_status"] not in {"PASS", "BLOCK"}
        ):
            blockers.append("selection_cell_contract_invalid")
            continue
        if (
            cell["strategy_id"] == strategy_id
            and cell["variant_id"] == variant_id
            and cell["lane"] == lane
        ):
            try:
                symbol = _clean_symbol(cell["symbol"])
            except ValueError:
                blockers.append("selection_cell_contract_invalid")
                continue
            if symbol in outcomes:
                blockers.append("selection_cell_coverage_invalid")
            else:
                outcomes[symbol] = cell["gate_status"]
    if set(outcomes) != set(expected_symbols):
        blockers.append("selection_cell_coverage_invalid")
    return outcomes, sorted(set(blockers))


def _seal_gate(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "gate_hash": _sha256(payload)}


def evaluate_correlation_cluster_gate(
    preregistration: Any,
    correlation_matrix: Any,
    selection_cells: Any,
    *,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    base = {
        "schema_version": GATE_SCHEMA_VERSION,
        "strategy_id": strategy_id if type(strategy_id) is str else "",
        "variant_id": variant_id if type(variant_id) is str else "",
        "lane": lane if type(lane) is str else "",
        "preregistration_hash": "",
        "matrix_hash": "",
        "status": "BLOCK",
        "first_blocking_tier": "PREREGISTRATION",
        "tiers": [],
        "cluster_results": [],
        "passing_cluster_count": 0,
        "required_cluster_votes": None,
        "cross_cluster_conflicts": [],
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_new_report_schema": True,
        "permissions": dict(_PERMISSIONS),
    }
    identity_blockers: list[str] = []
    try:
        _clean_identity(strategy_id, "strategy_id")
        _clean_identity(variant_id, "variant_id")
    except (TypeError, ValueError):
        identity_blockers.append("gate_identity_invalid")
    if type(lane) is not str or lane not in LANES:
        identity_blockers.append("gate_lane_invalid")

    prereg_check = verify_correlation_cluster_preregistration(preregistration)
    prereg_blockers = list(prereg_check["blockers"]) + identity_blockers
    clusters = preregistration.get("clusters", []) if type(preregistration) is dict else []
    if not prereg_blockers and len(clusters) < MINIMUM_INDEPENDENT_CLUSTERS:
        prereg_blockers.append("insufficient_preregistered_independent_clusters")
    if prereg_blockers:
        base["tiers"] = [
            {"tier_id": "PREREGISTRATION", "status": "BLOCK", "blockers": sorted(set(prereg_blockers))},
            {"tier_id": "COVERAGE", "status": "NOT_EVALUATED", "blockers": []},
            {"tier_id": "TOPOLOGY", "status": "NOT_EVALUATED", "blockers": []},
            {"tier_id": "CLUSTER_VOTE", "status": "NOT_EVALUATED", "blockers": []},
        ]
        return _seal_gate(base)

    symbols = preregistration["symbols"]
    base["preregistration_hash"] = preregistration["preregistration_hash"]
    matrix_check = verify_correlation_matrix_contract(correlation_matrix, expected_symbols=symbols)
    outcomes, cell_blockers = _selection_outcomes(
        selection_cells,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
        expected_symbols=symbols,
    )
    coverage_blockers = list(matrix_check["blockers"]) + cell_blockers
    if not coverage_blockers:
        low_overlap = any(
            pair["overlap_observations"] < MINIMUM_PAIR_OVERLAP
            for pair in correlation_matrix["pairs"]
        )
        if low_overlap:
            coverage_blockers.append("correlation_pair_overlap_insufficient")
    if coverage_blockers:
        base["first_blocking_tier"] = "COVERAGE"
        base["tiers"] = [
            {"tier_id": "PREREGISTRATION", "status": "PASS", "blockers": []},
            {"tier_id": "COVERAGE", "status": "BLOCK", "blockers": sorted(set(coverage_blockers))},
            {"tier_id": "TOPOLOGY", "status": "NOT_EVALUATED", "blockers": []},
            {"tier_id": "CLUSTER_VOTE", "status": "NOT_EVALUATED", "blockers": []},
        ]
        return _seal_gate(base)

    base["matrix_hash"] = correlation_matrix["matrix_hash"]
    symbol_cluster = {
        symbol: cluster["cluster_id"]
        for cluster in clusters
        for symbol in cluster["members"]
    }
    conflicts = [
        {
            "left_symbol": pair["left_symbol"],
            "right_symbol": pair["right_symbol"],
            "pearson_correlation": pair["pearson_correlation"],
        }
        for pair in correlation_matrix["pairs"]
        if (
            symbol_cluster[pair["left_symbol"]] != symbol_cluster[pair["right_symbol"]]
            and abs(pair["pearson_correlation"]) >= ABSOLUTE_PEARSON_THRESHOLD
        )
    ]
    base["cross_cluster_conflicts"] = conflicts
    if conflicts:
        base["tiers"] = [
            {"tier_id": "PREREGISTRATION", "status": "PASS", "blockers": []},
            {"tier_id": "COVERAGE", "status": "PASS", "blockers": []},
            {"tier_id": "TOPOLOGY", "status": "BLOCK", "blockers": ["cross_cluster_correlation_requires_new_preregistration"]},
            {"tier_id": "CLUSTER_VOTE", "status": "NOT_EVALUATED", "blockers": []},
        ]
        base["first_blocking_tier"] = "TOPOLOGY"
        return _seal_gate(base)

    cluster_results = []
    for cluster in clusters:
        member_outcomes = [
            {"symbol": symbol, "status": outcomes[symbol]}
            for symbol in cluster["members"]
        ]
        cluster_results.append({
            "cluster_id": cluster["cluster_id"],
            "status": "PASS" if all(item["status"] == "PASS" for item in member_outcomes) else "BLOCK",
            "member_outcomes": member_outcomes,
            "vote_count": 1,
        })
    passing = sum(result["status"] == "PASS" for result in cluster_results)
    required = math.ceil(len(cluster_results) * REQUIRED_CLUSTER_FRACTION)
    vote_passed = passing >= required
    base.update({
        "status": "PASS" if vote_passed else "BLOCK",
        "first_blocking_tier": None if vote_passed else "CLUSTER_VOTE",
        "cluster_results": cluster_results,
        "passing_cluster_count": passing,
        "required_cluster_votes": required,
        "tiers": [
            {"tier_id": "PREREGISTRATION", "status": "PASS", "blockers": []},
            {"tier_id": "COVERAGE", "status": "PASS", "blockers": []},
            {"tier_id": "TOPOLOGY", "status": "PASS", "blockers": []},
            {
                "tier_id": "CLUSTER_VOTE",
                "status": "PASS" if vote_passed else "BLOCK",
                "blockers": [] if vote_passed else ["cluster_vote_threshold_not_met"],
            },
        ],
    })
    return _seal_gate(base)


__all__ = [
    "ABSOLUTE_PEARSON_THRESHOLD",
    "CORRELATION_MATRIX_SCHEMA_VERSION",
    "GATE_SCHEMA_VERSION",
    "LANES",
    "LOOKBACK_OBSERVATIONS",
    "MINIMUM_INDEPENDENT_CLUSTERS",
    "MINIMUM_PAIR_OVERLAP",
    "PREREGISTRATION_SCHEMA_VERSION",
    "REQUIRED_CLUSTER_FRACTION",
    "RETURN_SERIES",
    "build_correlation_cluster_preregistration",
    "build_correlation_matrix_contract",
    "evaluate_correlation_cluster_gate",
    "verify_correlation_cluster_preregistration",
    "verify_correlation_matrix_contract",
]
