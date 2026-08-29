from __future__ import annotations

from datetime import date
import hashlib
import json
from typing import Any

from . import strategy_correlation_cluster_gate as source_contract
from .execution_authority import authority_violations


MATRIX_SCHEMA_VERSION = "strategy-selection-correlation-common-support-matrix-v2"
GATE_SCHEMA_VERSION = "strategy-correlation-cluster-common-support-gate-v2"
STATIC_FINGERPRINT = "20260822-strategy-correlation-cluster-common-support-gate-2"
COMMON_OBSERVATION_POLICY = "LISTWISE_COMPLETE_COMPLETED_DAILY_RETURNS"
MINIMUM_COMMON_OBSERVATIONS = source_contract.MINIMUM_PAIR_OVERLAP
MAXIMUM_COMMON_OBSERVATIONS = source_contract.LOOKBACK_OBSERVATIONS

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


def _normalize_common_observation_index(value: Any) -> list[str]:
    if type(value) is not list:
        raise ValueError("common observation index must be a list")
    if not MINIMUM_COMMON_OBSERVATIONS <= len(value) <= MAXIMUM_COMMON_OBSERVATIONS:
        raise ValueError("common observation index count is outside registered bounds")
    normalized: list[str] = []
    for item in value:
        if type(item) is not str or item != item.strip() or not item:
            raise ValueError("common observation labels must be trimmed strings")
        try:
            parsed = date.fromisoformat(item)
        except ValueError as error:
            raise ValueError("common observation labels must be canonical ISO dates") from error
        if parsed.isoformat() != item:
            raise ValueError("common observation labels must be canonical ISO dates")
        normalized.append(item)
    if normalized != sorted(normalized) or len(set(normalized)) != len(normalized):
        raise ValueError("common observation index must be strictly increasing and unique")
    return normalized


def build_common_support_correlation_matrix_v2(
    symbols: list[str],
    correlations: dict[tuple[str, str], float],
    common_observation_index: list[str],
) -> dict[str, Any]:
    common_index = _normalize_common_observation_index(common_observation_index)
    source_matrix = source_contract.build_correlation_matrix_contract(
        symbols,
        correlations,
        overlap_observations=len(common_index),
    )
    pairs = [
        {
            "left_symbol": pair["left_symbol"],
            "right_symbol": pair["right_symbol"],
            "pearson_correlation": pair["pearson_correlation"],
        }
        for pair in source_matrix["pairs"]
    ]
    body = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "status": "PASS",
        "return_series": source_contract.RETURN_SERIES,
        "lookback_observations": source_contract.LOOKBACK_OBSERVATIONS,
        "minimum_common_observations": MINIMUM_COMMON_OBSERVATIONS,
        "maximum_common_observations": MAXIMUM_COMMON_OBSERVATIONS,
        "common_observation_policy": COMMON_OBSERVATION_POLICY,
        "common_observation_count": len(common_index),
        "common_observation_index_hash": _sha256(common_index),
        "symbols": source_matrix["symbols"],
        "pairs": pairs,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "matrix_hash": _sha256(body)}


def verify_common_support_correlation_matrix_v2(
    document: Any,
    *,
    expected_symbols: list[str],
    common_observation_index: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["common_support_matrix_contract_invalid"])
    if _authority_invalid(document):
        blockers.append("execution_authority_invalid")
    expected_keys = {
        "schema_version",
        "status",
        "return_series",
        "lookback_observations",
        "minimum_common_observations",
        "maximum_common_observations",
        "common_observation_policy",
        "common_observation_count",
        "common_observation_index_hash",
        "symbols",
        "pairs",
        "permissions",
        "matrix_hash",
    }
    if set(document) != expected_keys:
        blockers.append("common_support_matrix_contract_invalid")
        return _verification(blockers)
    pairs = document.get("pairs")
    if type(pairs) is not list:
        blockers.append("common_support_matrix_contract_invalid")
        return _verification(blockers)
    correlations: dict[tuple[str, str], float] = {}
    for pair in pairs:
        if type(pair) is not dict or set(pair) != {
            "left_symbol",
            "right_symbol",
            "pearson_correlation",
        }:
            blockers.append("common_support_matrix_contract_invalid")
            continue
        key = (pair["left_symbol"], pair["right_symbol"])
        if key in correlations:
            blockers.append("common_support_matrix_contract_invalid")
        else:
            correlations[key] = pair["pearson_correlation"]
    if blockers:
        return _verification(blockers)
    try:
        rebuilt = build_common_support_correlation_matrix_v2(
            expected_symbols,
            correlations,
            common_observation_index,
        )
    except (MemoryError, TypeError, ValueError):
        blockers.append("common_support_matrix_contract_invalid")
        return _verification(blockers)
    if document != rebuilt:
        blockers.append("common_support_matrix_contract_invalid")
    return _verification(blockers)


def _sealed(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "gate_hash": _sha256(payload)}


def _base(strategy_id: Any, variant_id: Any, lane: Any) -> dict[str, Any]:
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "strategy_id": strategy_id if type(strategy_id) is str else "",
        "variant_id": variant_id if type(variant_id) is str else "",
        "lane": lane if type(lane) is str else "",
        "source_preregistration_hash": "",
        "common_support_matrix_hash": "",
        "common_observation_policy": COMMON_OBSERVATION_POLICY,
        "common_observation_count": None,
        "common_observation_index_hash": "",
        "common_support_verified": False,
        "source_gate_hash": "",
        "source_gate_status": "NOT_EVALUATED",
        "source_first_blocking_tier": None,
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


def evaluate_correlation_cluster_common_support_gate_v2(
    preregistration: Any,
    common_support_matrix: Any,
    common_observation_index: Any,
    selection_cells: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    result = _base(strategy_id, variant_id, lane)
    preregistration_check = source_contract.verify_correlation_cluster_preregistration(
        preregistration
    )
    if preregistration_check["status"] != "PASS":
        result["tiers"] = [
            {
                "tier_id": "PREREGISTRATION",
                "status": "BLOCK",
                "blockers": preregistration_check["blockers"],
            },
            {"tier_id": "COMMON_SUPPORT", "status": "NOT_EVALUATED", "blockers": []},
            {"tier_id": "SOURCE_CLUSTER_GATE", "status": "NOT_EVALUATED", "blockers": []},
        ]
        return _sealed(result)

    result["source_preregistration_hash"] = preregistration["preregistration_hash"]
    matrix_check = verify_common_support_correlation_matrix_v2(
        common_support_matrix,
        expected_symbols=preregistration["symbols"],
        common_observation_index=common_observation_index,
    )
    if matrix_check["status"] != "PASS":
        result["first_blocking_tier"] = "COMMON_SUPPORT"
        result["tiers"] = [
            {"tier_id": "PREREGISTRATION", "status": "PASS", "blockers": []},
            {
                "tier_id": "COMMON_SUPPORT",
                "status": "BLOCK",
                "blockers": matrix_check["blockers"],
            },
            {"tier_id": "SOURCE_CLUSTER_GATE", "status": "NOT_EVALUATED", "blockers": []},
        ]
        return _sealed(result)

    correlations = {
        (pair["left_symbol"], pair["right_symbol"]): pair["pearson_correlation"]
        for pair in common_support_matrix["pairs"]
    }
    try:
        source_matrix = source_contract.build_correlation_matrix_contract(
            common_support_matrix["symbols"],
            correlations,
            overlap_observations=common_support_matrix["common_observation_count"],
        )
        source_result = source_contract.evaluate_correlation_cluster_gate(
            preregistration,
            source_matrix,
            selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (MemoryError, TypeError, ValueError):
        result["first_blocking_tier"] = "SOURCE_CLUSTER_GATE"
        result["tiers"] = [
            {"tier_id": "PREREGISTRATION", "status": "PASS", "blockers": []},
            {"tier_id": "COMMON_SUPPORT", "status": "PASS", "blockers": []},
            {
                "tier_id": "SOURCE_CLUSTER_GATE",
                "status": "BLOCK",
                "blockers": ["source_cluster_gate_error"],
            },
        ]
        return _sealed(result)

    result.update(
        {
            "common_support_matrix_hash": common_support_matrix["matrix_hash"],
            "common_observation_count": common_support_matrix[
                "common_observation_count"
            ],
            "common_observation_index_hash": common_support_matrix[
                "common_observation_index_hash"
            ],
            "common_support_verified": True,
            "source_gate_hash": source_result["gate_hash"],
            "source_gate_status": source_result["status"],
            "source_first_blocking_tier": source_result["first_blocking_tier"],
            "status": source_result["status"],
            "first_blocking_tier": (
                None if source_result["status"] == "PASS" else "SOURCE_CLUSTER_GATE"
            ),
            "cluster_results": source_result["cluster_results"],
            "passing_cluster_count": source_result["passing_cluster_count"],
            "required_cluster_votes": source_result["required_cluster_votes"],
            "cross_cluster_conflicts": source_result["cross_cluster_conflicts"],
            "tiers": [
                {"tier_id": "PREREGISTRATION", "status": "PASS", "blockers": []},
                {"tier_id": "COMMON_SUPPORT", "status": "PASS", "blockers": []},
                {
                    "tier_id": "SOURCE_CLUSTER_GATE",
                    "status": source_result["status"],
                    "blockers": (
                        []
                        if source_result["status"] == "PASS"
                        else ["source_cluster_gate_blocked"]
                    ),
                },
            ],
        }
    )
    return _sealed(result)


def verify_correlation_cluster_common_support_gate_v2(
    document: Any,
    preregistration: Any,
    common_support_matrix: Any,
    common_observation_index: Any,
    selection_cells: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = evaluate_correlation_cluster_common_support_gate_v2(
            preregistration,
            common_support_matrix,
            common_observation_index,
            selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (KeyError, MemoryError, TypeError, ValueError):
        return False
    return document == expected


__all__ = [
    "COMMON_OBSERVATION_POLICY",
    "GATE_SCHEMA_VERSION",
    "MATRIX_SCHEMA_VERSION",
    "MAXIMUM_COMMON_OBSERVATIONS",
    "MINIMUM_COMMON_OBSERVATIONS",
    "STATIC_FINGERPRINT",
    "build_common_support_correlation_matrix_v2",
    "evaluate_correlation_cluster_common_support_gate_v2",
    "verify_common_support_correlation_matrix_v2",
    "verify_correlation_cluster_common_support_gate_v2",
]
