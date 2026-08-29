"""Dynamic-window correlation source and independent-ticket gate v2.

The legacy v1 source is intentionally fixed to a 60-observation window.  This
unmounted v2 contract makes a non-60 lookback explicit, binds it to the frozen
cluster partition, rebuilds full pair coverage and complete-link topology, and
counts at most one effective vote per correlation cluster.

This module is pure and research-only.  It does not read runtime data, mount a
consumer, activate current, place orders, or grant paper/live authority.
"""

from __future__ import annotations

import copy
import hmac
from itertools import combinations
import math
import re
from typing import Any

from exchange_terminal.services import strategy_correlation_cluster_gate as legacy
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-window-source-preregistration-v2"
)
MATRIX_SCHEMA_VERSION = "strategy-selection-correlation-window-matrix-v2"
GATE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-window-independent-ticket-gate-v2"
)
PREREGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    f"{PREREGISTRATION_SCHEMA_VERSION}-verification-v1"
)
MATRIX_VERIFICATION_SCHEMA_VERSION = f"{MATRIX_SCHEMA_VERSION}-verification-v1"
GATE_VERIFICATION_SCHEMA_VERSION = f"{GATE_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260825-correlation-cluster-window-source-v2-lock-1"
MINIMUM_LOOKBACK_OBSERVATIONS = 20
MAXIMUM_LOOKBACK_OBSERVATIONS = 2520
MINIMUM_OVERLAP_NUMERATOR = 2
MINIMUM_OVERLAP_DENOMINATOR = 3
TOPOLOGY_RULE = "COMPLETE_LINK_WITH_NO_CROSS_CLUSTER_THRESHOLD_CONFLICT"
VOTE_RULE = "ALL_MEMBERS_PASS_ONE_EFFECTIVE_VOTE_PER_CLUSTER"

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOW_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_CELL_KEYS = {"strategy_id", "variant_id", "symbol", "lane", "gate_status"}
_PAIR_KEYS = {
    "left_symbol",
    "right_symbol",
    "overlap_observations",
    "pearson_correlation",
}


class CorrelationWindowSourceContractError(ValueError):
    """Raised when a v2 source cannot be represented canonically."""


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verification(schema_version: str, blockers: list[str], **facts: Any) -> dict[str, Any]:
    unique = sorted(set(blockers))
    return {
        "schema_version": schema_version,
        "status": "BLOCK" if unique else "PASS",
        "blockers": unique,
        **facts,
        "authority": _authority(),
    }


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _identity(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 128
    ):
        raise CorrelationWindowSourceContractError(f"{label} is invalid")
    return value


def _window_id(value: Any) -> str:
    if type(value) is not str or _WINDOW_ID_RE.fullmatch(value) is None:
        raise CorrelationWindowSourceContractError("window_id is invalid")
    return value


def _lookback(value: Any) -> int:
    if (
        type(value) is not int
        or isinstance(value, bool)
        or value < MINIMUM_LOOKBACK_OBSERVATIONS
        or value > MAXIMUM_LOOKBACK_OBSERVATIONS
    ):
        raise CorrelationWindowSourceContractError("lookback_observations is invalid")
    return value


def _minimum_overlap(lookback: int) -> int:
    return math.ceil(
        lookback * MINIMUM_OVERLAP_NUMERATOR / MINIMUM_OVERLAP_DENOMINATOR
    )


def _symbol(value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise CorrelationWindowSourceContractError("symbol is invalid")
    return value.strip().upper()


def _finite_correlation(value: Any) -> float:
    if type(value) not in {int, float} or not math.isfinite(float(value)):
        raise CorrelationWindowSourceContractError("correlation is not finite")
    parsed = float(value)
    if parsed < -1.0 or parsed > 1.0:
        raise CorrelationWindowSourceContractError("correlation is out of range")
    return parsed


def _normalize_pair_mapping(values: Any, label: str) -> dict[tuple[str, str], Any]:
    if type(values) is not dict:
        raise CorrelationWindowSourceContractError(f"{label} must be a dictionary")
    normalized: dict[tuple[str, str], Any] = {}
    for raw_pair, value in values.items():
        if type(raw_pair) is not tuple or len(raw_pair) != 2:
            raise CorrelationWindowSourceContractError(f"{label} pair is invalid")
        left, right = sorted((_symbol(raw_pair[0]), _symbol(raw_pair[1])))
        if left == right or (left, right) in normalized:
            raise CorrelationWindowSourceContractError(
                f"{label} pairs must be unique distinct symbols"
            )
        normalized[(left, right)] = value
    return normalized


def build_correlation_cluster_window_source_preregistration_v2(
    *,
    window_id: Any,
    lookback_observations: Any,
    clusters: Any,
) -> dict[str, Any]:
    """Freeze a dynamic window and an exact cluster partition before evidence."""
    clean_window_id = _window_id(window_id)
    lookback = _lookback(lookback_observations)
    try:
        partition = legacy.build_correlation_cluster_preregistration(
            copy.deepcopy(clusters)
        )
    except (MemoryError, TypeError, ValueError) as exc:
        raise CorrelationWindowSourceContractError("cluster partition is invalid") from exc
    if len(partition["clusters"]) < legacy.MINIMUM_INDEPENDENT_CLUSTERS:
        raise CorrelationWindowSourceContractError(
            "at least two preregistered clusters are required"
        )
    body = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "STRUCTURALLY_PREREGISTERED_RESEARCH_ONLY",
        "window_id": clean_window_id,
        "return_series": legacy.RETURN_SERIES,
        "lookback_observations": lookback,
        "minimum_pair_overlap": _minimum_overlap(lookback),
        "minimum_overlap_policy": (
            "CEIL_TWO_THIRDS_OF_PREREGISTERED_LOOKBACK"
        ),
        "absolute_pearson_threshold": legacy.ABSOLUTE_PEARSON_THRESHOLD,
        "topology_rule": TOPOLOGY_RULE,
        "cluster_vote_rule": VOTE_RULE,
        "minimum_independent_clusters": legacy.MINIMUM_INDEPENDENT_CLUSTERS,
        "required_cluster_fraction": legacy.REQUIRED_CLUSTER_FRACTION,
        "symbols": list(partition["symbols"]),
        "clusters": copy.deepcopy(partition["clusters"]),
        "legacy_partition_preregistration_hash": partition["preregistration_hash"],
        "facts": {
            "structural_preregistration_only": True,
            "chronology_independently_proven": False,
            "window_data_observed_by_builder": False,
            "runtime_sources_accessed": False,
            "current_activated": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(body, "preregistration_v2_hash")


def verify_correlation_cluster_window_source_preregistration_v2(
    document: Any,
    *,
    expected_preregistration_v2_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(
            PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
            ["window_source_preregistration_object_required"],
            preregistration_v2_hash=None,
        )
    if not _same_hash(
        document.get("preregistration_v2_hash"),
        expected_preregistration_v2_hash,
    ):
        blockers.append("window_source_preregistration_expected_hash_mismatch")
    try:
        rebuilt = build_correlation_cluster_window_source_preregistration_v2(
            window_id=document.get("window_id"),
            lookback_observations=document.get("lookback_observations"),
            clusters=document.get("clusters"),
        )
        if not strict_json_contract_equal(document, rebuilt):
            blockers.append("window_source_preregistration_contract_invalid")
    except Exception:
        blockers.append("window_source_preregistration_contract_invalid")
    return _verification(
        PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        blockers,
        preregistration_v2_hash=(
            document.get("preregistration_v2_hash") if not blockers else None
        ),
    )


def build_correlation_cluster_window_matrix_v2(
    preregistration: Any,
    correlations: Any,
    *,
    overlap_observations: Any,
) -> dict[str, Any]:
    if type(preregistration) is not dict:
        raise CorrelationWindowSourceContractError("preregistration is invalid")
    preregistration_hash = preregistration.get("preregistration_v2_hash")
    verification = verify_correlation_cluster_window_source_preregistration_v2(
        preregistration,
        expected_preregistration_v2_hash=preregistration_hash,
    )
    if verification["status"] != "PASS":
        raise CorrelationWindowSourceContractError("preregistration is invalid")
    symbols = list(preregistration["symbols"])
    expected_pairs = set(combinations(symbols, 2))
    normalized_correlations = _normalize_pair_mapping(correlations, "correlations")
    if set(normalized_correlations) != expected_pairs:
        raise CorrelationWindowSourceContractError(
            "correlations must cover every symbol pair exactly once"
        )
    if type(overlap_observations) is dict:
        normalized_overlaps = _normalize_pair_mapping(
            overlap_observations,
            "overlap_observations",
        )
        if set(normalized_overlaps) != expected_pairs:
            raise CorrelationWindowSourceContractError(
                "overlaps must cover every symbol pair exactly once"
            )
    else:
        normalized_overlaps = {pair: overlap_observations for pair in expected_pairs}
    pairs: list[dict[str, Any]] = []
    for left, right in sorted(expected_pairs):
        correlation = _finite_correlation(normalized_correlations[(left, right)])
        overlap = normalized_overlaps[(left, right)]
        if (
            type(overlap) is not int
            or isinstance(overlap, bool)
            or overlap < 0
            or overlap > preregistration["lookback_observations"]
        ):
            raise CorrelationWindowSourceContractError(
                "overlap must be a native integer within the preregistered lookback"
            )
        pairs.append(
            {
                "left_symbol": left,
                "right_symbol": right,
                "overlap_observations": overlap,
                "pearson_correlation": correlation,
            }
        )
    body = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "preregistration_v2_hash": preregistration_hash,
        "window_id": preregistration["window_id"],
        "return_series": preregistration["return_series"],
        "lookback_observations": preregistration["lookback_observations"],
        "minimum_pair_overlap": preregistration["minimum_pair_overlap"],
        "symbols": symbols,
        "pairs": pairs,
        "facts": {
            "expected_pair_count": len(expected_pairs),
            "observed_pair_count": len(pairs),
            "pair_coverage_complete": True,
            "runtime_sources_accessed": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(body, "matrix_v2_hash")


def verify_correlation_cluster_window_matrix_v2(
    document: Any,
    preregistration: Any,
    *,
    expected_preregistration_v2_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    preregistration_verification = (
        verify_correlation_cluster_window_source_preregistration_v2(
            preregistration,
            expected_preregistration_v2_hash=expected_preregistration_v2_hash,
        )
    )
    if preregistration_verification["status"] != "PASS":
        blockers.append("window_source_preregistration_invalid")
    if type(document) is not dict:
        blockers.append("window_matrix_object_required")
        return _verification(
            MATRIX_VERIFICATION_SCHEMA_VERSION,
            blockers,
            matrix_v2_hash=None,
        )
    pairs = document.get("pairs")
    correlations: dict[tuple[str, str], Any] = {}
    overlaps: dict[tuple[str, str], Any] = {}
    pair_shape_valid = type(pairs) is list
    if pair_shape_valid:
        for row in pairs:
            if type(row) is not dict or set(row) != _PAIR_KEYS:
                pair_shape_valid = False
                break
            left = row.get("left_symbol")
            right = row.get("right_symbol")
            if type(left) is not str or type(right) is not str or left >= right:
                pair_shape_valid = False
                break
            pair = (left, right)
            if pair in correlations:
                pair_shape_valid = False
                break
            correlations[pair] = row.get("pearson_correlation")
            overlaps[pair] = row.get("overlap_observations")
    if not pair_shape_valid:
        blockers.append("window_matrix_pair_contract_invalid")
    if not blockers:
        try:
            rebuilt = build_correlation_cluster_window_matrix_v2(
                preregistration,
                correlations,
                overlap_observations=overlaps,
            )
            if not strict_json_contract_equal(document, rebuilt):
                blockers.append("window_matrix_contract_invalid")
        except Exception:
            blockers.append("window_matrix_contract_invalid")
    return _verification(
        MATRIX_VERIFICATION_SCHEMA_VERSION,
        blockers,
        matrix_v2_hash=document.get("matrix_v2_hash") if not blockers else None,
    )


def _selection_outcomes(
    cells: Any,
    *,
    strategy_id: str,
    variant_id: str,
    lane: str,
    symbols: list[str],
) -> tuple[dict[str, str], list[str]]:
    blockers: list[str] = []
    outcomes: dict[str, str] = {}
    if type(cells) is not list:
        return outcomes, ["selection_cells_not_list"]
    for cell in cells:
        if type(cell) is not dict or set(cell) != _CELL_KEYS:
            blockers.append("selection_cell_contract_invalid")
            continue
        try:
            symbol = _symbol(cell["symbol"])
        except CorrelationWindowSourceContractError:
            blockers.append("selection_cell_contract_invalid")
            continue
        if (
            cell["strategy_id"] != strategy_id
            or cell["variant_id"] != variant_id
            or cell["lane"] != lane
            or cell["symbol"] != symbol
            or type(cell["gate_status"]) is not str
            or cell["gate_status"] not in {"PASS", "BLOCK"}
            or symbol in outcomes
        ):
            blockers.append("selection_cell_contract_invalid")
            continue
        outcomes[symbol] = cell["gate_status"]
    if set(outcomes) != set(symbols) or len(cells) != len(symbols):
        blockers.append("selection_cell_coverage_invalid")
    return outcomes, sorted(set(blockers))


def _seal_gate(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "gate_v2_hash")


def evaluate_correlation_cluster_window_independent_ticket_gate_v2(
    preregistration: Any,
    matrix: Any,
    selection_cells: Any,
    *,
    expected_preregistration_v2_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "decision": "BLOCK_WINDOW_SOURCE_UNVERIFIED",
        "strategy_id": strategy_id if type(strategy_id) is str else "",
        "variant_id": variant_id if type(variant_id) is str else "",
        "lane": lane if type(lane) is str else "",
        "preregistration_v2_hash": None,
        "matrix_v2_hash": None,
        "first_blocking_tier": "SOURCE",
        "tiers": [],
        "cluster_results": [],
        "coverage_conflicts": [],
        "topology_conflicts": [],
        "raw_passing_symbol_ticket_count": 0,
        "effective_independent_ticket_count": 0,
        "discounted_correlated_ticket_count": 0,
        "required_independent_cluster_votes": None,
        "facts": {
            "dynamic_window_bound": False,
            "complete_pair_coverage_verified": False,
            "complete_link_topology_verified": False,
            "correlated_symbols_counted_as_independent": False,
            "current_activated": False,
            "runtime_sources_accessed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }
    source_blockers: list[str] = []
    try:
        clean_strategy_id = _identity(strategy_id, "strategy_id")
        clean_variant_id = _identity(variant_id, "variant_id")
    except CorrelationWindowSourceContractError:
        clean_strategy_id = ""
        clean_variant_id = ""
        source_blockers.append("gate_identity_invalid")
    if type(lane) is not str or lane not in legacy.LANES:
        source_blockers.append("gate_lane_invalid")
    preregistration_check = verify_correlation_cluster_window_source_preregistration_v2(
        preregistration,
        expected_preregistration_v2_hash=expected_preregistration_v2_hash,
    )
    if preregistration_check["status"] != "PASS":
        source_blockers.append("window_source_preregistration_invalid")
    matrix_check = verify_correlation_cluster_window_matrix_v2(
        matrix,
        preregistration,
        expected_preregistration_v2_hash=expected_preregistration_v2_hash,
    )
    if matrix_check["status"] != "PASS":
        source_blockers.append("window_matrix_invalid")
    symbols = list(preregistration.get("symbols") or []) if type(preregistration) is dict else []
    outcomes, cell_blockers = _selection_outcomes(
        selection_cells,
        strategy_id=clean_strategy_id,
        variant_id=clean_variant_id,
        lane=lane if type(lane) is str else "",
        symbols=symbols,
    )
    source_blockers.extend(cell_blockers)
    if source_blockers:
        base["tiers"] = [
            {"tier_id": "SOURCE", "status": "BLOCK", "blockers": sorted(set(source_blockers))},
            {"tier_id": "COVERAGE", "status": "NOT_EVALUATED", "blockers": []},
            {"tier_id": "TOPOLOGY", "status": "NOT_EVALUATED", "blockers": []},
            {"tier_id": "CLUSTER_VOTE", "status": "NOT_EVALUATED", "blockers": []},
        ]
        return _seal_gate(base)

    base["preregistration_v2_hash"] = preregistration["preregistration_v2_hash"]
    base["matrix_v2_hash"] = matrix["matrix_v2_hash"]
    base["facts"]["dynamic_window_bound"] = True
    minimum_overlap = preregistration["minimum_pair_overlap"]
    coverage_conflicts = [
        {
            "left_symbol": row["left_symbol"],
            "right_symbol": row["right_symbol"],
            "overlap_observations": row["overlap_observations"],
            "minimum_pair_overlap": minimum_overlap,
        }
        for row in matrix["pairs"]
        if row["overlap_observations"] < minimum_overlap
    ]
    base["coverage_conflicts"] = coverage_conflicts
    if coverage_conflicts:
        base.update(
            {
                "status": "BLOCK",
                "decision": "BLOCK_WINDOW_PAIR_OVERLAP_INSUFFICIENT",
                "first_blocking_tier": "COVERAGE",
                "tiers": [
                    {"tier_id": "SOURCE", "status": "PASS", "blockers": []},
                    {"tier_id": "COVERAGE", "status": "BLOCK", "blockers": ["window_pair_overlap_insufficient"]},
                    {"tier_id": "TOPOLOGY", "status": "NOT_EVALUATED", "blockers": []},
                    {"tier_id": "CLUSTER_VOTE", "status": "NOT_EVALUATED", "blockers": []},
                ],
            }
        )
        return _seal_gate(base)
    base["facts"]["complete_pair_coverage_verified"] = True

    symbol_cluster = {
        member: cluster["cluster_id"]
        for cluster in preregistration["clusters"]
        for member in cluster["members"]
    }
    topology_conflicts: list[dict[str, Any]] = []
    threshold = preregistration["absolute_pearson_threshold"]
    for row in matrix["pairs"]:
        left = row["left_symbol"]
        right = row["right_symbol"]
        correlation = row["pearson_correlation"]
        same_cluster = symbol_cluster[left] == symbol_cluster[right]
        if same_cluster and abs(correlation) < threshold:
            topology_conflicts.append(
                {**row, "reason": "INTERNAL_PAIR_BELOW_COMPLETE_LINK_THRESHOLD"}
            )
        elif not same_cluster and abs(correlation) >= threshold:
            topology_conflicts.append(
                {**row, "reason": "CROSS_CLUSTER_THRESHOLD_CONFLICT"}
            )
    base["topology_conflicts"] = topology_conflicts
    if topology_conflicts:
        base.update(
            {
                "status": "BLOCK",
                "decision": "BLOCK_WINDOW_CLUSTER_TOPOLOGY_DRIFT",
                "first_blocking_tier": "TOPOLOGY",
                "tiers": [
                    {"tier_id": "SOURCE", "status": "PASS", "blockers": []},
                    {"tier_id": "COVERAGE", "status": "PASS", "blockers": []},
                    {"tier_id": "TOPOLOGY", "status": "BLOCK", "blockers": ["window_cluster_topology_invalid"]},
                    {"tier_id": "CLUSTER_VOTE", "status": "NOT_EVALUATED", "blockers": []},
                ],
            }
        )
        return _seal_gate(base)
    base["facts"]["complete_link_topology_verified"] = True

    cluster_results: list[dict[str, Any]] = []
    for cluster in preregistration["clusters"]:
        member_outcomes = [
            {"symbol": member, "status": outcomes[member]}
            for member in cluster["members"]
        ]
        passed = all(row["status"] == "PASS" for row in member_outcomes)
        cluster_results.append(
            {
                "cluster_id": cluster["cluster_id"],
                "status": "PASS" if passed else "BLOCK",
                "member_outcomes": member_outcomes,
                "effective_vote_count": 1 if passed else 0,
            }
        )
    raw_passing = sum(status == "PASS" for status in outcomes.values())
    effective = sum(row["status"] == "PASS" for row in cluster_results)
    required = max(
        preregistration["minimum_independent_clusters"],
        math.ceil(
            len(cluster_results) * preregistration["required_cluster_fraction"]
        ),
    )
    vote_passed = effective >= required
    base.update(
        {
            "status": "PASS" if vote_passed else "BLOCK",
            "decision": (
                "PASS_DYNAMIC_WINDOW_INDEPENDENT_TICKET_RESEARCH_GATE"
                if vote_passed
                else "BLOCK_DYNAMIC_WINDOW_INDEPENDENT_CLUSTER_VOTES"
            ),
            "first_blocking_tier": None if vote_passed else "CLUSTER_VOTE",
            "cluster_results": cluster_results,
            "raw_passing_symbol_ticket_count": raw_passing,
            "effective_independent_ticket_count": effective,
            "discounted_correlated_ticket_count": max(0, raw_passing - effective),
            "required_independent_cluster_votes": required,
            "tiers": [
                {"tier_id": "SOURCE", "status": "PASS", "blockers": []},
                {"tier_id": "COVERAGE", "status": "PASS", "blockers": []},
                {"tier_id": "TOPOLOGY", "status": "PASS", "blockers": []},
                {
                    "tier_id": "CLUSTER_VOTE",
                    "status": "PASS" if vote_passed else "BLOCK",
                    "blockers": [] if vote_passed else ["independent_cluster_vote_threshold_not_met"],
                },
            ],
        }
    )
    return _seal_gate(base)


def verify_correlation_cluster_window_independent_ticket_gate_v2(
    document: Any,
    preregistration: Any,
    matrix: Any,
    selection_cells: Any,
    *,
    expected_preregistration_v2_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_correlation_cluster_window_independent_ticket_gate_v2(
            preregistration,
            matrix,
            selection_cells,
            expected_preregistration_v2_hash=expected_preregistration_v2_hash,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
        exact = type(document) is dict and strict_json_contract_equal(document, expected)
    except Exception:
        expected = {}
        exact = False
    return _verification(
        GATE_VERIFICATION_SCHEMA_VERSION,
        [] if exact else ["window_independent_ticket_gate_contract_invalid"],
        gate_status=expected.get("status") if exact else "UNKNOWN",
        gate_decision=expected.get("decision") if exact else "UNKNOWN",
        gate_v2_hash=expected.get("gate_v2_hash") if exact else None,
    )


__all__ = [
    "CorrelationWindowSourceContractError",
    "GATE_SCHEMA_VERSION",
    "MATRIX_SCHEMA_VERSION",
    "PREREGISTRATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_correlation_cluster_window_matrix_v2",
    "build_correlation_cluster_window_source_preregistration_v2",
    "evaluate_correlation_cluster_window_independent_ticket_gate_v2",
    "verify_correlation_cluster_window_independent_ticket_gate_v2",
    "verify_correlation_cluster_window_matrix_v2",
    "verify_correlation_cluster_window_source_preregistration_v2",
]
