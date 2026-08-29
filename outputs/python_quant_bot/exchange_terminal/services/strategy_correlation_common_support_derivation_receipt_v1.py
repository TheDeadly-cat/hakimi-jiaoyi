from __future__ import annotations

from copy import deepcopy
import hashlib
from itertools import combinations
import json
import math
from typing import Any

from . import strategy_correlation_cluster_common_support_gate_v2 as common_support
from . import strategy_correlation_return_replay as source_replay
from .execution_authority import authority_violations


RECEIPT_SCHEMA_VERSION = "strategy-correlation-common-support-derivation-receipt-v1"
GATE_SCHEMA_VERSION = "strategy-correlation-common-support-derived-gate-v1"
STATIC_FINGERPRINT = "20260822-strategy-correlation-common-support-derivation-receipt-1"
COMMON_PRICE_INDEX_POLICY = "LATEST_UP_TO_61_LISTWISE_COMPLETE_COMPLETED_DAILY_CLOSES"
PEARSON_METHOD = "TWO_PASS_FSUM_CENTERED_PEARSON"
DERIVATION_SCOPE = (
    "LOCAL_VERIFIED_REPLAY_TO_LISTWISE_COMMON_SUPPORT_NOT_EXTERNAL_MARKET_TRUTH"
)
MINIMUM_COMMON_PRICE_ROWS = common_support.MINIMUM_COMMON_OBSERVATIONS + 1
MAXIMUM_COMMON_PRICE_ROWS = common_support.MAXIMUM_COMMON_OBSERVATIONS + 1

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


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("common_support_pair_observations_insufficient")
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    left_delta = [value - left_mean for value in left]
    right_delta = [value - right_mean for value in right]
    numerator = math.fsum(a * b for a, b in zip(left_delta, right_delta))
    left_energy = math.fsum(value * value for value in left_delta)
    right_energy = math.fsum(value * value for value in right_delta)
    denominator = math.sqrt(left_energy * right_energy)
    if not math.isfinite(denominator) or denominator <= 0:
        raise ValueError("common_support_pair_variance_zero")
    result = numerator / denominator
    if not math.isfinite(result) or abs(result) > 1.000000000001:
        raise ValueError("common_support_pair_result_invalid")
    return max(-1.0, min(1.0, result))


def _derive_common_support(matrix_replay: Any) -> dict[str, Any]:
    source_check = source_replay.verify_correlation_matrix_replay(matrix_replay)
    if source_check["status"] != "PASS":
        raise ValueError("source_matrix_replay_invalid")

    completed_input = matrix_replay["completed_price_input"]
    prices_by_symbol: dict[str, dict[str, float]] = {}
    for dataset in completed_input["datasets"]:
        prices_by_symbol[dataset["symbol"]] = {
            row["date"]: row["close"] for row in dataset["price_rows"]
        }
    symbols = sorted(prices_by_symbol)
    if len(symbols) < 2:
        raise ValueError("common_support_symbol_coverage_invalid")

    common_price_dates = sorted(
        set.intersection(*(set(prices_by_symbol[symbol]) for symbol in symbols))
    )[-MAXIMUM_COMMON_PRICE_ROWS:]
    if len(common_price_dates) < MINIMUM_COMMON_PRICE_ROWS:
        raise ValueError("common_price_rows_insufficient")

    common_observation_index = common_price_dates[1:]
    returns_by_symbol: dict[str, list[float]] = {}
    for symbol in symbols:
        prices = prices_by_symbol[symbol]
        values: list[float] = []
        for previous_date, current_date in zip(
            common_price_dates,
            common_price_dates[1:],
        ):
            value = prices[current_date] / prices[previous_date] - 1.0
            if not math.isfinite(value):
                raise ValueError("common_support_return_nonfinite")
            values.append(value)
        returns_by_symbol[symbol] = values

    correlations = {
        (left, right): _pearson(returns_by_symbol[left], returns_by_symbol[right])
        for left, right in combinations(symbols, 2)
    }
    matrix = common_support.build_common_support_correlation_matrix_v2(
        symbols,
        correlations,
        common_observation_index,
    )
    matrix_check = common_support.verify_common_support_correlation_matrix_v2(
        matrix,
        expected_symbols=symbols,
        common_observation_index=common_observation_index,
    )
    if matrix_check["status"] != "PASS":
        raise ValueError("derived_common_support_matrix_invalid")
    return {
        "common_price_index": common_price_dates,
        "common_observation_index": common_observation_index,
        "common_support_matrix": matrix,
    }


def build_correlation_common_support_derivation_receipt_v1(
    matrix_replay: dict[str, Any],
) -> dict[str, Any]:
    derived = _derive_common_support(matrix_replay)
    matrix = derived["common_support_matrix"]
    common_price_index = derived["common_price_index"]
    common_observation_index = derived["common_observation_index"]
    body = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "derivation_scope": DERIVATION_SCOPE,
        "source_replay_status": "PASS",
        "source_matrix_replay_hash": matrix_replay["replay_hash"],
        "source_completed_price_input_hash": matrix_replay["completed_price_input"][
            "input_hash"
        ],
        "source_pairwise_matrix_hash": matrix_replay["correlation_matrix"][
            "matrix_hash"
        ],
        "source_preregistration_hash": matrix_replay["preregistration"][
            "preregistration_hash"
        ],
        "return_method": source_replay.RETURN_METHOD,
        "pearson_method": PEARSON_METHOD,
        "common_price_index_policy": COMMON_PRICE_INDEX_POLICY,
        "common_price_row_count": len(common_price_index),
        "common_price_index_hash": _sha256(common_price_index),
        "common_observation_policy": common_support.COMMON_OBSERVATION_POLICY,
        "common_observation_count": len(common_observation_index),
        "common_observation_index_hash": _sha256(common_observation_index),
        "common_support_matrix": deepcopy(matrix),
        "common_support_matrix_hash": matrix["matrix_hash"],
        "derivation_verified": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_new_report_schema": True,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "receipt_hash": _sha256(body)}


_RECEIPT_KEYS = {
    "schema_version",
    "static_fingerprint",
    "status",
    "derivation_scope",
    "source_replay_status",
    "source_matrix_replay_hash",
    "source_completed_price_input_hash",
    "source_pairwise_matrix_hash",
    "source_preregistration_hash",
    "return_method",
    "pearson_method",
    "common_price_index_policy",
    "common_price_row_count",
    "common_price_index_hash",
    "common_observation_policy",
    "common_observation_count",
    "common_observation_index_hash",
    "common_support_matrix",
    "common_support_matrix_hash",
    "derivation_verified",
    "current_writer_activation_allowed",
    "current_admission_allowed",
    "requires_new_report_schema",
    "permissions",
    "receipt_hash",
}


def verify_correlation_common_support_derivation_receipt_v1(
    document: Any,
    *,
    matrix_replay: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["common_support_derivation_receipt_invalid"])
    if _authority_invalid(document):
        blockers.append("execution_authority_invalid")
    if set(document) != _RECEIPT_KEYS:
        blockers.append("common_support_derivation_receipt_invalid")
        return _verification(blockers)
    try:
        rebuilt = build_correlation_common_support_derivation_receipt_v1(
            matrix_replay
        )
    except (ArithmeticError, KeyError, MemoryError, TypeError, ValueError):
        blockers.append("source_matrix_replay_invalid")
        return _verification(blockers)
    if document != rebuilt:
        blockers.append("common_support_derivation_receipt_semantic_mismatch")
    return _verification(blockers)


def _base(strategy_id: Any, variant_id: Any, lane: Any) -> dict[str, Any]:
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "strategy_id": strategy_id if type(strategy_id) is str else "",
        "variant_id": variant_id if type(variant_id) is str else "",
        "lane": lane if type(lane) is str else "",
        "source_derivation_receipt_hash": "",
        "source_matrix_replay_hash": "",
        "common_support_matrix_hash": "",
        "common_observation_count": None,
        "common_observation_index_hash": "",
        "derivation_verified": False,
        "source_common_support_gate_hash": "",
        "source_common_support_gate_status": "NOT_EVALUATED",
        "source_common_support_first_blocking_tier": None,
        "source_cluster_first_blocking_tier": None,
        "status": "BLOCK",
        "first_blocking_tier": "IDENTITY",
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


def _sealed(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "gate_hash": _sha256(payload)}


def evaluate_correlation_common_support_derived_gate_v1(
    derivation_receipt: Any,
    matrix_replay: Any,
    selection_cells: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    result = _base(strategy_id, variant_id, lane)
    identity_valid = (
        type(strategy_id) is str
        and bool(strategy_id)
        and strategy_id == strategy_id.strip()
        and type(variant_id) is str
        and bool(variant_id)
        and variant_id == variant_id.strip()
        and type(lane) is str
        and lane in source_replay.LANES
    )
    if not identity_valid:
        result["tiers"] = [
            {
                "tier_id": "IDENTITY",
                "status": "BLOCK",
                "blockers": ["derived_gate_identity_invalid"],
            },
            {"tier_id": "DERIVATION", "status": "NOT_EVALUATED", "blockers": []},
            {
                "tier_id": "COMMON_SUPPORT_GATE",
                "status": "NOT_EVALUATED",
                "blockers": [],
            },
        ]
        return _sealed(result)

    receipt_check = verify_correlation_common_support_derivation_receipt_v1(
        derivation_receipt,
        matrix_replay=matrix_replay,
    )
    if receipt_check["status"] != "PASS":
        result["first_blocking_tier"] = "DERIVATION"
        result["tiers"] = [
            {"tier_id": "IDENTITY", "status": "PASS", "blockers": []},
            {
                "tier_id": "DERIVATION",
                "status": "BLOCK",
                "blockers": receipt_check["blockers"],
            },
            {
                "tier_id": "COMMON_SUPPORT_GATE",
                "status": "NOT_EVALUATED",
                "blockers": [],
            },
        ]
        return _sealed(result)

    try:
        derived = _derive_common_support(matrix_replay)
        source_result = common_support.evaluate_correlation_cluster_common_support_gate_v2(
            matrix_replay["preregistration"],
            derivation_receipt["common_support_matrix"],
            derived["common_observation_index"],
            selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (ArithmeticError, KeyError, MemoryError, TypeError, ValueError):
        result["first_blocking_tier"] = "COMMON_SUPPORT_GATE"
        result["tiers"] = [
            {"tier_id": "IDENTITY", "status": "PASS", "blockers": []},
            {"tier_id": "DERIVATION", "status": "PASS", "blockers": []},
            {
                "tier_id": "COMMON_SUPPORT_GATE",
                "status": "BLOCK",
                "blockers": ["source_common_support_gate_error"],
            },
        ]
        return _sealed(result)

    result.update(
        {
            "source_derivation_receipt_hash": derivation_receipt["receipt_hash"],
            "source_matrix_replay_hash": matrix_replay["replay_hash"],
            "common_support_matrix_hash": derivation_receipt[
                "common_support_matrix_hash"
            ],
            "common_observation_count": derivation_receipt[
                "common_observation_count"
            ],
            "common_observation_index_hash": derivation_receipt[
                "common_observation_index_hash"
            ],
            "derivation_verified": True,
            "source_common_support_gate_hash": source_result["gate_hash"],
            "source_common_support_gate_status": source_result["status"],
            "source_common_support_first_blocking_tier": source_result[
                "first_blocking_tier"
            ],
            "source_cluster_first_blocking_tier": source_result[
                "source_first_blocking_tier"
            ],
            "status": source_result["status"],
            "first_blocking_tier": (
                None
                if source_result["status"] == "PASS"
                else "COMMON_SUPPORT_GATE"
            ),
            "tiers": [
                {"tier_id": "IDENTITY", "status": "PASS", "blockers": []},
                {"tier_id": "DERIVATION", "status": "PASS", "blockers": []},
                {
                    "tier_id": "COMMON_SUPPORT_GATE",
                    "status": source_result["status"],
                    "blockers": (
                        []
                        if source_result["status"] == "PASS"
                        else ["source_common_support_gate_blocked"]
                    ),
                },
            ],
            "cluster_results": source_result["cluster_results"],
            "passing_cluster_count": source_result["passing_cluster_count"],
            "required_cluster_votes": source_result["required_cluster_votes"],
            "cross_cluster_conflicts": source_result["cross_cluster_conflicts"],
        }
    )
    return _sealed(result)


def verify_correlation_common_support_derived_gate_v1(
    document: Any,
    derivation_receipt: Any,
    matrix_replay: Any,
    selection_cells: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> bool:
    if type(document) is not dict or _authority_invalid(document):
        return False
    try:
        expected = evaluate_correlation_common_support_derived_gate_v1(
            derivation_receipt,
            matrix_replay,
            selection_cells,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    except (ArithmeticError, KeyError, MemoryError, TypeError, ValueError):
        return False
    return document == expected


__all__ = [
    "COMMON_PRICE_INDEX_POLICY",
    "DERIVATION_SCOPE",
    "GATE_SCHEMA_VERSION",
    "MAXIMUM_COMMON_PRICE_ROWS",
    "MINIMUM_COMMON_PRICE_ROWS",
    "PEARSON_METHOD",
    "RECEIPT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_correlation_common_support_derivation_receipt_v1",
    "evaluate_correlation_common_support_derived_gate_v1",
    "verify_correlation_common_support_derivation_receipt_v1",
    "verify_correlation_common_support_derived_gate_v1",
]
