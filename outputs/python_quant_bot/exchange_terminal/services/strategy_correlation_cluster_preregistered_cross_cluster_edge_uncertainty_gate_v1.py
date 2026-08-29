"""Preregistered uncertainty gate for positive cross-cluster correlation edges.

The gate is intentionally isolated from runtime, current selectors, HTTP, paper,
and live execution. It prevents stable cluster partitions from being interpreted
as independent bets when pairwise positive-correlation estimates are too sparse
or their one-sided Fisher-z upper confidence bounds still overlap the frozen
cross-cluster correlation floor.
"""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import math
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-"
    "uncertainty-preregistration-v1"
)
EVIDENCE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-"
    "uncertainty-evidence-v1"
)
SCHEMA_VERSION = (
    "strategy-correlation-cluster-preregistered-cross-cluster-edge-"
    "uncertainty-gate-v1"
)
VERIFICATION_SCHEMA_VERSION = SCHEMA_VERSION + "-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-preregistered-cross-cluster-edge-uncertainty-gate-v1-"
    "unmounted-lock-1"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
MICRO_SCALE = 1_000_000
UNKNOWN_STATUS = "UNKNOWN"
PASS_STATUS = "PASS"
BLOCK_STATUS = "BLOCK"

_SOURCE_AUTHORITY_KEYS = {
    "live_order_allowed",
    "paper_authorized",
    "research_only",
    "symbol_universe_changes_allowed",
    "threshold_changes_allowed",
    "writer_allowed",
}
_PREREGISTRATION_KEYS = {
    "authority",
    "cluster_partition_hash",
    "confidence_z_micros",
    "correlation_floor_micros",
    "minimum_sample_count",
    "preregistration_hash",
    "registration_sequence",
    "schema_version",
    "symbol_clusters",
    "trade_identity_hash",
}
_SYMBOL_CLUSTER_KEYS = {"cluster_id", "symbol"}
_EVIDENCE_KEYS = {
    "cluster_partition_hash",
    "evidence_hash",
    "evidence_sequence",
    "pairs",
    "schema_version",
    "trade_identity_hash",
}
_PAIR_EVIDENCE_KEYS = {
    "left_symbol",
    "observed_correlation_micros",
    "right_symbol",
    "sample_count",
}


class CrossClusterEdgeUncertaintyContractError(ValueError):
    """Raised only by canonical source-document builders."""


def _exact_keys(value: Any, expected: set[str]) -> bool:
    return type(value) is dict and set(value) == expected


def _is_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool)


def _is_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _source_authority() -> dict[str, bool]:
    return {
        "live_order_allowed": False,
        "paper_authorized": False,
        "research_only": True,
        "symbol_universe_changes_allowed": False,
        "threshold_changes_allowed": False,
        "writer_allowed": False,
    }


def _authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "descriptive_only": True,
        "live_order_allowed": False,
        "local_research_gate_only": True,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


def _policy() -> dict[str, Any]:
    return {
        "confidence_method": "FISHER_Z_ONE_SIDED_UPPER",
        "insufficient_sample_action": "BLOCK",
        "pair_universe": "ALL_PREREGISTERED_CROSS_CLUSTER_PAIRS",
        "positive_correlation_dependence_only": True,
        "risk_reduction_is_not_execution_authority": True,
        "threshold_comparison": "BLOCK_IF_OBSERVED_OR_UPPER_GTE_FLOOR",
    }


def _sealed_document_valid(value: Any, hash_key: str) -> bool:
    if type(value) is not dict or not _is_hash(value.get(hash_key)):
        return False
    body = deepcopy(value)
    body.pop(hash_key, None)
    try:
        expected = seal_strict_canonical_document(body, hash_key)
        return strict_json_contract_equal(value, expected)
    except (KeyError, TypeError, ValueError):
        return False


def _symbol_rows_valid(value: Any) -> bool:
    if type(value) is not list or len(value) < 2:
        return False
    if not all(
        _exact_keys(row, _SYMBOL_CLUSTER_KEYS)
        and type(row["symbol"]) is str
        and bool(row["symbol"])
        and type(row["cluster_id"]) is str
        and bool(row["cluster_id"])
        for row in value
    ):
        return False
    symbols = [row["symbol"] for row in value]
    clusters = {row["cluster_id"] for row in value}
    return symbols == sorted(symbols) and len(set(symbols)) == len(symbols) and len(clusters) >= 2


def _preregistration_valid(value: Any) -> bool:
    if not _exact_keys(value, _PREREGISTRATION_KEYS):
        return False
    authority = value["authority"]
    return (
        value["schema_version"] == PREREGISTRATION_SCHEMA_VERSION
        and _sealed_document_valid(value, "preregistration_hash")
        and _is_hash(value["trade_identity_hash"])
        and _is_hash(value["cluster_partition_hash"])
        and _is_int(value["registration_sequence"])
        and value["registration_sequence"] >= 0
        and _is_int(value["correlation_floor_micros"])
        and 0 < value["correlation_floor_micros"] < MICRO_SCALE
        and _is_int(value["confidence_z_micros"])
        and 0 < value["confidence_z_micros"] <= 5 * MICRO_SCALE
        and _is_int(value["minimum_sample_count"])
        and value["minimum_sample_count"] >= 4
        and _symbol_rows_valid(value["symbol_clusters"])
        and _exact_keys(authority, _SOURCE_AUTHORITY_KEYS)
        and authority == _source_authority()
    )


def _pair_rows_valid(value: Any) -> bool:
    if type(value) is not list:
        return False
    if not all(
        _exact_keys(row, _PAIR_EVIDENCE_KEYS)
        and type(row["left_symbol"]) is str
        and bool(row["left_symbol"])
        and type(row["right_symbol"]) is str
        and bool(row["right_symbol"])
        and row["left_symbol"] < row["right_symbol"]
        and _is_int(row["observed_correlation_micros"])
        and 0 <= row["observed_correlation_micros"] < MICRO_SCALE
        and _is_int(row["sample_count"])
        and row["sample_count"] >= 4
        for row in value
    ):
        return False
    pair_ids = [(row["left_symbol"], row["right_symbol"]) for row in value]
    return pair_ids == sorted(pair_ids) and len(set(pair_ids)) == len(pair_ids)


def _evidence_valid(value: Any) -> bool:
    return (
        _exact_keys(value, _EVIDENCE_KEYS)
        and value["schema_version"] == EVIDENCE_SCHEMA_VERSION
        and _sealed_document_valid(value, "evidence_hash")
        and _is_hash(value["trade_identity_hash"])
        and _is_hash(value["cluster_partition_hash"])
        and _is_int(value["evidence_sequence"])
        and value["evidence_sequence"] >= 0
        and _pair_rows_valid(value["pairs"])
    )


def _cross_cluster_pairs(symbol_clusters: list[dict[str, str]]) -> list[tuple[str, str]]:
    cluster_by_symbol = {row["symbol"]: row["cluster_id"] for row in symbol_clusters}
    symbols = sorted(cluster_by_symbol)
    return [
        (left, right)
        for left, right in combinations(symbols, 2)
        if cluster_by_symbol[left] != cluster_by_symbol[right]
    ]


def _confidence_upper_micros(
    observed_correlation_micros: int,
    sample_count: int,
    confidence_z_micros: int,
) -> int:
    correlation = observed_correlation_micros / MICRO_SCALE
    z_score = confidence_z_micros / MICRO_SCALE
    fisher_upper = math.atanh(correlation) + z_score / math.sqrt(sample_count - 3)
    upper = math.tanh(fisher_upper)
    return min(MICRO_SCALE - 1, max(observed_correlation_micros, round(upper * MICRO_SCALE)))


def build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_preregistration_v1(
    symbol_clusters: Any,
    *,
    trade_identity_hash: Any,
    cluster_partition_hash: Any,
    registration_sequence: Any,
    correlation_floor_micros: Any,
    confidence_z_micros: Any,
    minimum_sample_count: Any,
) -> dict[str, Any]:
    """Build a sealed preregistration with canonical symbol order."""
    try:
        rows = sorted(
            [
                {"cluster_id": row["cluster_id"], "symbol": row["symbol"]}
                for row in deepcopy(symbol_clusters)
            ],
            key=lambda row: row["symbol"],
        )
    except (KeyError, TypeError):
        rows = None
    document = {
        "authority": _source_authority(),
        "cluster_partition_hash": cluster_partition_hash,
        "confidence_z_micros": confidence_z_micros,
        "correlation_floor_micros": correlation_floor_micros,
        "minimum_sample_count": minimum_sample_count,
        "registration_sequence": registration_sequence,
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "symbol_clusters": rows,
        "trade_identity_hash": trade_identity_hash,
    }
    sealed = seal_strict_canonical_document(document, "preregistration_hash")
    if not _preregistration_valid(sealed):
        raise CrossClusterEdgeUncertaintyContractError("preregistration contract invalid")
    return sealed


def build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_evidence_v1(
    pairs: Any,
    *,
    trade_identity_hash: Any,
    cluster_partition_hash: Any,
    evidence_sequence: Any,
) -> dict[str, Any]:
    """Build sealed evidence with canonical pair order."""
    try:
        rows = sorted(
            [
                {
                    "left_symbol": row["left_symbol"],
                    "observed_correlation_micros": row[
                        "observed_correlation_micros"
                    ],
                    "right_symbol": row["right_symbol"],
                    "sample_count": row["sample_count"],
                }
                for row in deepcopy(pairs)
            ],
            key=lambda row: (row["left_symbol"], row["right_symbol"]),
        )
    except (KeyError, TypeError):
        rows = None
    document = {
        "cluster_partition_hash": cluster_partition_hash,
        "evidence_sequence": evidence_sequence,
        "pairs": rows,
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "trade_identity_hash": trade_identity_hash,
    }
    sealed = seal_strict_canonical_document(document, "evidence_hash")
    if not _evidence_valid(sealed):
        raise CrossClusterEdgeUncertaintyContractError("evidence contract invalid")
    return sealed


def _unknown(reason: str) -> dict[str, Any]:
    document = {
        "authority": _authority(),
        "blockers": [reason],
        "decision": "UNKNOWN_CROSS_CLUSTER_EDGE_UNCERTAINTY_SOURCE",
        "facts": {
            "complete_cross_cluster_pair_universe_verified": False,
            "evidence_exactly_verified": False,
            "historical_market_data_accessed": False,
            "pair_uncertainty_evaluated": False,
            "preregistration_exactly_verified": False,
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "source_documents_embedded": False,
        },
        "pair_results": [],
        "policy": _policy(),
        "schema_version": SCHEMA_VERSION,
        "source": {
            "cluster_partition_hash": None,
            "evidence_hash": None,
            "preregistration_hash": None,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "trade_identity_hash": None,
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": UNKNOWN_STATUS,
        "summary": {
            "blocked_pair_count": None,
            "clear_pair_count": None,
            "confidence_z_micros": None,
            "correlation_floor_micros": None,
            "insufficient_sample_pair_count": None,
            "maximum_confidence_upper_correlation_micros": None,
            "minimum_sample_count": None,
            "observed_breach_pair_count": None,
            "preregistered_cross_cluster_pair_count": None,
            "preregistered_symbol_count": None,
            "uncertainty_overlap_pair_count": None,
            "verified_pair_count": None,
        },
    }
    return seal_strict_canonical_document(document, "edge_uncertainty_gate_v1_hash")


def evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
    preregistration: Any,
    evidence: Any,
    *,
    expected_preregistration_hash: Any,
) -> dict[str, Any]:
    """Evaluate every preregistered cross-cluster pair and fail closed."""
    if not _is_hash(expected_preregistration_hash):
        return _unknown("EXPECTED_PREREGISTRATION_HASH_INVALID")
    if not _preregistration_valid(preregistration):
        return _unknown("PREREGISTRATION_CONTRACT_INVALID")
    if preregistration["preregistration_hash"] != expected_preregistration_hash:
        return _unknown("PREREGISTRATION_HASH_SUBSTITUTED")
    if not _evidence_valid(evidence):
        return _unknown("EVIDENCE_CONTRACT_INVALID")
    if (
        evidence["trade_identity_hash"] != preregistration["trade_identity_hash"]
        or evidence["cluster_partition_hash"]
        != preregistration["cluster_partition_hash"]
    ):
        return _unknown("SOURCE_IDENTITY_SPLICE")
    if evidence["evidence_sequence"] <= preregistration["registration_sequence"]:
        return _unknown("EVIDENCE_NOT_AFTER_PREREGISTRATION")

    expected_pairs = _cross_cluster_pairs(preregistration["symbol_clusters"])
    actual_pairs = [
        (row["left_symbol"], row["right_symbol"])
        for row in evidence["pairs"]
    ]
    if actual_pairs != expected_pairs:
        return _unknown("CROSS_CLUSTER_PAIR_UNIVERSE_MISMATCH")

    cluster_by_symbol = {
        row["symbol"]: row["cluster_id"]
        for row in preregistration["symbol_clusters"]
    }
    floor = preregistration["correlation_floor_micros"]
    minimum_sample = preregistration["minimum_sample_count"]
    confidence_z = preregistration["confidence_z_micros"]
    pair_results = []
    for row in evidence["pairs"]:
        observed = row["observed_correlation_micros"]
        sample_count = row["sample_count"]
        upper = _confidence_upper_micros(observed, sample_count, confidence_z)
        if observed >= floor:
            classification = "OBSERVED_CROSS_CLUSTER_EDGE_AT_OR_ABOVE_FLOOR"
            status = BLOCK_STATUS
        elif sample_count < minimum_sample:
            classification = "INSUFFICIENT_SAMPLE_FOR_CROSS_CLUSTER_EDGE"
            status = BLOCK_STATUS
        elif upper >= floor:
            classification = "UNCERTAINTY_INTERVAL_OVERLAPS_CORRELATION_FLOOR"
            status = BLOCK_STATUS
        else:
            classification = "CLEAR_BELOW_PREREGISTERED_CORRELATION_FLOOR"
            status = PASS_STATUS
        pair_results.append(
            {
                "classification": classification,
                "confidence_upper_correlation_micros": upper,
                "left_cluster_id": cluster_by_symbol[row["left_symbol"]],
                "left_symbol": row["left_symbol"],
                "observed_correlation_micros": observed,
                "right_cluster_id": cluster_by_symbol[row["right_symbol"]],
                "right_symbol": row["right_symbol"],
                "sample_count": sample_count,
                "status": status,
            }
        )

    blocked = [row for row in pair_results if row["status"] == BLOCK_STATUS]
    local_status = BLOCK_STATUS if blocked else PASS_STATUS
    decision = (
        "BLOCK_PREREGISTERED_CROSS_CLUSTER_EDGE_UNCERTAINTY"
        if blocked
        else "PASS_PREREGISTERED_CROSS_CLUSTER_EDGE_UNCERTAINTY"
    )
    blockers = sorted({row["classification"] for row in blocked})
    document = {
        "authority": _authority(),
        "blockers": blockers,
        "decision": decision,
        "facts": {
            "complete_cross_cluster_pair_universe_verified": True,
            "evidence_exactly_verified": True,
            "historical_market_data_accessed": False,
            "pair_uncertainty_evaluated": True,
            "preregistration_exactly_verified": True,
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "source_documents_embedded": False,
        },
        "pair_results": pair_results,
        "policy": _policy(),
        "schema_version": SCHEMA_VERSION,
        "source": {
            "cluster_partition_hash": preregistration["cluster_partition_hash"],
            "evidence_hash": evidence["evidence_hash"],
            "preregistration_hash": preregistration["preregistration_hash"],
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "trade_identity_hash": preregistration["trade_identity_hash"],
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": local_status,
        "summary": {
            "blocked_pair_count": len(blocked),
            "clear_pair_count": sum(
                row["status"] == PASS_STATUS for row in pair_results
            ),
            "confidence_z_micros": confidence_z,
            "correlation_floor_micros": floor,
            "insufficient_sample_pair_count": sum(
                row["classification"]
                == "INSUFFICIENT_SAMPLE_FOR_CROSS_CLUSTER_EDGE"
                for row in pair_results
            ),
            "maximum_confidence_upper_correlation_micros": max(
                row["confidence_upper_correlation_micros"]
                for row in pair_results
            ),
            "minimum_sample_count": minimum_sample,
            "observed_breach_pair_count": sum(
                row["classification"]
                == "OBSERVED_CROSS_CLUSTER_EDGE_AT_OR_ABOVE_FLOOR"
                for row in pair_results
            ),
            "preregistered_cross_cluster_pair_count": len(expected_pairs),
            "preregistered_symbol_count": len(
                preregistration["symbol_clusters"]
            ),
            "uncertainty_overlap_pair_count": sum(
                row["classification"]
                == "UNCERTAINTY_INTERVAL_OVERLAPS_CORRELATION_FLOOR"
                for row in pair_results
            ),
            "verified_pair_count": len(pair_results),
        },
    }
    return seal_strict_canonical_document(document, "edge_uncertainty_gate_v1_hash")


def verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
    document: Any,
    preregistration: Any,
    evidence: Any,
    *,
    expected_preregistration_hash: Any,
) -> dict[str, Any]:
    """Return an authority-locked exact-rebuild receipt."""
    try:
        expected = evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1(
            preregistration,
            evidence,
            expected_preregistration_hash=expected_preregistration_hash,
        )
        exact = strict_json_contract_equal(document, expected)
    except (KeyError, TypeError, ValueError):
        expected = None
        exact = False
    gate_hash = expected.get("edge_uncertainty_gate_v1_hash") if exact else None
    gate_status = expected.get("status") if exact else UNKNOWN_STATUS
    return {
        "blockers": [] if exact else ["EDGE_UNCERTAINTY_GATE_V1_EXACT_REBUILD_FAILED"],
        "current_admission_allowed": False,
        "edge_uncertainty_gate_v1_exactly_verified": exact,
        "edge_uncertainty_gate_v1_hash": gate_hash,
        "gate_decision": expected.get("decision") if exact else "UNKNOWN",
        "gate_status": gate_status,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "source_known": exact and gate_status in {PASS_STATUS, BLOCK_STATUS},
        "status": PASS_STATUS if exact else BLOCK_STATUS,
        "writer_allowed": False,
    }


__all__ = [
    "BLOCK_STATUS",
    "CrossClusterEdgeUncertaintyContractError",
    "EVIDENCE_SCHEMA_VERSION",
    "MICRO_SCALE",
    "PASS_STATUS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "UNKNOWN_STATUS",
    "VERIFICATION_SCHEMA_VERSION",
    "build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_evidence_v1",
    "build_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_preregistration_v1",
    "evaluate_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1",
    "verify_strategy_correlation_cluster_preregistered_cross_cluster_edge_uncertainty_gate_v1",
]
