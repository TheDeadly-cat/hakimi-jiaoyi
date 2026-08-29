"""Unmounted positive-semidefinite geometry gate for correlation matrices."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any

from exchange_terminal.services.strategy_correlation_cluster_gate import (
    CORRELATION_MATRIX_SCHEMA_VERSION,
    verify_correlation_matrix_contract,
)


SCHEMA_VERSION = "strategy-correlation-matrix-geometry-gate-contract-v1"
PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-preregistration-v1"
)
GATE_SCHEMA_VERSION = "strategy-correlation-matrix-geometry-gate-v1"
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-gate-v1-unmounted-lock-1"
)
EIGEN_SOLVER = "SYMMETRIC_JACOBI_V1"
PAIR_BOUND_TOLERANCE = 1e-12
PSD_TOLERANCE = 1e-10
CONVERGENCE_TOLERANCE = 1e-14
MAXIMUM_DIMENSION = 64
MAXIMUM_SWEEP_MULTIPLIER = 50
GATE_CONTRACT_HASH = (
    "ecefe7b0fe09edc3bb5d5b925b4acb731930b3e91af91edc8790c45cfa24b863"
)

_LOWER_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_ACTIVATION_ORDER = (
    "VERIFY_UPSTREAM_MATRIX_CONTRACT",
    "EVALUATE_MATRIX_GEOMETRY",
    "RUN_COMPLETE_LINK_AUDIT",
    "RUN_CLUSTER_GATE",
    "RUN_STRATIFIED_STABILITY",
    "RUN_EFFECTIVE_BET_BUDGET",
    "CONSIDER_PRESENTATION",
)
_BASE_BLOCKERS = (
    "UNMOUNTED_CANDIDATE",
    "CONSUMER_ORDER_NOT_ACTIVATED",
    "NO_MARKET_RUNTIME_EVIDENCE",
    "PAPER_LIVE_UNAUTHORIZED",
)
_AUTHORITY = {
    "descriptive_research_only": True,
    "consumer_activation_authorized": False,
    "http_registration_authorized": False,
    "runtime_activation_authorized": False,
    "paper_authorized": False,
    "live_authorized": False,
    "profitability_claimed": False,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _seal(document: Mapping[str, Any], field: str) -> dict[str, Any]:
    sealed = dict(document)
    sealed[field] = _canonical_hash(document)
    return sealed


def _is_lower_hex_64(value: Any) -> bool:
    return isinstance(value, str) and _LOWER_HEX_64.fullmatch(value) is not None


def _stable_float(value: float) -> float:
    if abs(value) < 5e-16:
        return 0.0
    return float(format(value, ".15g"))


def _parameters() -> dict[str, Any]:
    return {
        "eigen_solver": EIGEN_SOLVER,
        "pair_bound_tolerance": PAIR_BOUND_TOLERANCE,
        "psd_tolerance": PSD_TOLERANCE,
        "convergence_tolerance": CONVERGENCE_TOLERANCE,
        "maximum_dimension": MAXIMUM_DIMENSION,
        "maximum_sweep_multiplier": MAXIMUM_SWEEP_MULTIPLIER,
    }


def build_strategy_correlation_matrix_geometry_preregistration_v1(
    expected_symbols: Any,
) -> dict[str, Any] | None:
    if (
        not isinstance(expected_symbols, list)
        or not 2 <= len(expected_symbols) <= MAXIMUM_DIMENSION
        or any(
            not isinstance(symbol, str) or not symbol.strip()
            for symbol in expected_symbols
        )
        or len(set(expected_symbols)) != len(expected_symbols)
    ):
        return None
    symbols = list(expected_symbols)
    preregistration = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "expected_symbols": symbols,
        "symbol_order_hash": _canonical_hash(symbols),
        "parameters": _parameters(),
        "activation_order": list(_ACTIVATION_ORDER),
        "facts": {
            "thresholds_caller_overridable": False,
            "geometry_gate_precedes_complete_link": True,
            "geometry_gate_precedes_effective_budget": True,
            "synthetic_only": True,
            "mounted": False,
        },
        "blockers": list(_BASE_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(preregistration, "preregistration_hash")


def verify_strategy_correlation_matrix_geometry_preregistration_v1(
    document: Any,
    *,
    expected_symbols: Any,
    expected_preregistration_hash: Any,
) -> bool:
    rebuilt = build_strategy_correlation_matrix_geometry_preregistration_v1(
        expected_symbols
    )
    return (
        isinstance(document, Mapping)
        and rebuilt is not None
        and _is_lower_hex_64(expected_preregistration_hash)
        and document == rebuilt
        and document.get("preregistration_hash")
        == expected_preregistration_hash
    )


def _reconstruct_matrix(
    correlation_matrix: Mapping[str, Any],
    symbols: list[str],
) -> list[list[float]] | None:
    pairs = correlation_matrix.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != len(symbols) * (len(symbols) - 1) // 2:
        return None
    positions = {symbol: index for index, symbol in enumerate(symbols)}
    matrix = [
        [1.0 if row == column else 0.0 for column in range(len(symbols))]
        for row in range(len(symbols))
    ]
    seen: set[tuple[int, int]] = set()
    for pair in pairs:
        if not isinstance(pair, Mapping):
            return None
        left = pair.get("left_symbol")
        right = pair.get("right_symbol")
        value = pair.get("pearson_correlation")
        if (
            left not in positions
            or right not in positions
            or left == right
            or isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or abs(float(value)) > 1.0 + PAIR_BOUND_TOLERANCE
        ):
            return None
        left_index = positions[left]
        right_index = positions[right]
        key = tuple(sorted((left_index, right_index)))
        if key in seen:
            return None
        seen.add(key)
        matrix[left_index][right_index] = float(value)
        matrix[right_index][left_index] = float(value)
    return matrix


def _jacobi_eigenvalues(
    matrix: list[list[float]],
) -> tuple[list[float], bool, int, float]:
    dimension = len(matrix)
    working = [row[:] for row in matrix]
    maximum_iterations = MAXIMUM_SWEEP_MULTIPLIER * dimension * dimension
    residual = 0.0
    for iteration in range(maximum_iterations + 1):
        residual = 0.0
        pivot_row = 0
        pivot_column = 1
        for row in range(dimension):
            for column in range(row + 1, dimension):
                candidate = abs(working[row][column])
                if candidate > residual:
                    residual = candidate
                    pivot_row = row
                    pivot_column = column
        if residual <= CONVERGENCE_TOLERANCE:
            return (
                sorted(_stable_float(working[index][index]) for index in range(dimension)),
                True,
                iteration,
                _stable_float(residual),
            )
        row = pivot_row
        column = pivot_column
        diagonal_row = working[row][row]
        diagonal_column = working[column][column]
        off_diagonal = working[row][column]
        angle = 0.5 * math.atan2(
            2.0 * off_diagonal,
            diagonal_column - diagonal_row,
        )
        cosine = math.cos(angle)
        sine = math.sin(angle)
        for index in range(dimension):
            if index in (row, column):
                continue
            row_value = working[index][row]
            column_value = working[index][column]
            working[index][row] = working[row][index] = (
                cosine * row_value - sine * column_value
            )
            working[index][column] = working[column][index] = (
                sine * row_value + cosine * column_value
            )
        working[row][row] = (
            cosine * cosine * diagonal_row
            - 2.0 * sine * cosine * off_diagonal
            + sine * sine * diagonal_column
        )
        working[column][column] = (
            sine * sine * diagonal_row
            + 2.0 * sine * cosine * off_diagonal
            + cosine * cosine * diagonal_column
        )
        working[row][column] = 0.0
        working[column][row] = 0.0
    return (
        sorted(_stable_float(working[index][index]) for index in range(dimension)),
        False,
        maximum_iterations,
        _stable_float(residual),
    )


def _build_gate_result(
    preregistration: Mapping[str, Any],
    correlation_matrix: Mapping[str, Any],
    *,
    status: str,
    reason_code: str,
    upstream_verification: Mapping[str, Any],
    geometry: Mapping[str, Any] | None,
    gate_blockers: list[str],
) -> dict[str, Any]:
    result = {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "reason_code": reason_code,
        "synthetic_only": True,
        "mounted": False,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "preregistration_hash": preregistration["preregistration_hash"],
        "matrix_hash": correlation_matrix.get("matrix_hash"),
        "symbol_order_hash": preregistration["symbol_order_hash"],
        "upstream_verification": deepcopy(upstream_verification),
        "geometry": deepcopy(geometry),
        "facts": {
            "upstream_matrix_contract_passed": (
                upstream_verification.get("status") == "PASS"
            ),
            "pairwise_bounds_are_not_psd_proof": True,
            "geometry_evaluated_before_complete_link": True,
            "geometry_evaluated_before_effective_budget": True,
            "market_runtime_evidence_used": False,
        },
        "gate_blockers": gate_blockers,
        "activation_blockers": list(_BASE_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(result, "gate_hash")


def evaluate_strategy_correlation_matrix_geometry_gate_v1(
    preregistration: Any,
    correlation_matrix: Any,
    *,
    expected_preregistration_hash: Any,
) -> dict[str, Any] | None:
    if not isinstance(preregistration, Mapping) or not isinstance(
        correlation_matrix, Mapping
    ):
        return None
    expected_symbols = preregistration.get("expected_symbols")
    if not verify_strategy_correlation_matrix_geometry_preregistration_v1(
        preregistration,
        expected_symbols=expected_symbols,
        expected_preregistration_hash=expected_preregistration_hash,
    ):
        return None
    upstream = verify_correlation_matrix_contract(
        correlation_matrix,
        expected_symbols=expected_symbols,
    )
    if not isinstance(upstream, Mapping) or upstream.get("status") != "PASS":
        return _build_gate_result(
            preregistration,
            correlation_matrix,
            status="UNKNOWN",
            reason_code="UPSTREAM_MATRIX_CONTRACT_NOT_PASS",
            upstream_verification=(
                upstream if isinstance(upstream, Mapping) else {"status": "UNKNOWN"}
            ),
            geometry=None,
            gate_blockers=["UPSTREAM_MATRIX_CONTRACT_NOT_PASS"],
        )
    if correlation_matrix.get("symbols") != expected_symbols:
        return _build_gate_result(
            preregistration,
            correlation_matrix,
            status="UNKNOWN",
            reason_code="SYMBOL_ORDER_MISMATCH",
            upstream_verification=upstream,
            geometry=None,
            gate_blockers=["SYMBOL_ORDER_MISMATCH"],
        )
    matrix = _reconstruct_matrix(correlation_matrix, expected_symbols)
    if matrix is None:
        return _build_gate_result(
            preregistration,
            correlation_matrix,
            status="UNKNOWN",
            reason_code="MATRIX_GEOMETRY_INPUT_NOT_RECONSTRUCTABLE",
            upstream_verification=upstream,
            geometry=None,
            gate_blockers=["MATRIX_GEOMETRY_INPUT_NOT_RECONSTRUCTABLE"],
        )
    eigenvalues, converged, iterations, residual = _jacobi_eigenvalues(matrix)
    minimum_eigenvalue = min(eigenvalues)
    negative_count = sum(value < -PSD_TOLERANCE for value in eigenvalues)
    geometry = {
        "dimension": len(matrix),
        "pair_count": len(correlation_matrix["pairs"]),
        "eigen_solver": EIGEN_SOLVER,
        "eigenvalues": eigenvalues,
        "minimum_eigenvalue": minimum_eigenvalue,
        "negative_eigenvalue_count": negative_count,
        "psd_tolerance": PSD_TOLERANCE,
        "converged": converged,
        "iterations": iterations,
        "maximum_off_diagonal_residual": residual,
    }
    if not converged:
        return _build_gate_result(
            preregistration,
            correlation_matrix,
            status="UNKNOWN",
            reason_code="EIGEN_SOLVER_NOT_CONVERGED",
            upstream_verification=upstream,
            geometry=geometry,
            gate_blockers=["EIGEN_SOLVER_NOT_CONVERGED"],
        )
    if negative_count:
        return _build_gate_result(
            preregistration,
            correlation_matrix,
            status="BLOCK",
            reason_code="CORRELATION_MATRIX_NOT_POSITIVE_SEMIDEFINITE",
            upstream_verification=upstream,
            geometry=geometry,
            gate_blockers=["CORRELATION_MATRIX_NOT_POSITIVE_SEMIDEFINITE"],
        )
    return _build_gate_result(
        preregistration,
        correlation_matrix,
        status="PASS",
        reason_code="CORRELATION_MATRIX_GEOMETRY_ACCEPTED",
        upstream_verification=upstream,
        geometry=geometry,
        gate_blockers=[],
    )


def verify_strategy_correlation_matrix_geometry_gate_v1(
    document: Any,
    preregistration: Any,
    correlation_matrix: Any,
    *,
    expected_preregistration_hash: Any,
) -> bool:
    if not isinstance(document, Mapping):
        return False
    expected = evaluate_strategy_correlation_matrix_geometry_gate_v1(
        preregistration,
        correlation_matrix,
        expected_preregistration_hash=expected_preregistration_hash,
    )
    return expected is not None and document == expected


__all__ = [
    "CONVERGENCE_TOLERANCE",
    "EIGEN_SOLVER",
    "GATE_CONTRACT_HASH",
    "GATE_SCHEMA_VERSION",
    "MAXIMUM_DIMENSION",
    "PAIR_BOUND_TOLERANCE",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PSD_TOLERANCE",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_matrix_geometry_preregistration_v1",
    "evaluate_strategy_correlation_matrix_geometry_gate_v1",
    "verify_strategy_correlation_matrix_geometry_gate_v1",
    "verify_strategy_correlation_matrix_geometry_preregistration_v1",
]
