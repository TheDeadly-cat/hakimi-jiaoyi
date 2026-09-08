from __future__ import annotations

from copy import deepcopy
from datetime import date
import hashlib
from itertools import combinations
import json
import math
from typing import Any

from hakimi_research.candle_contract import candle_is_complete

from .execution_authority import authority_violations
from .strategy_correlation_cluster_gate import (
    LANES,
    LOOKBACK_OBSERVATIONS,
    build_correlation_matrix_contract,
    evaluate_correlation_cluster_gate,
    verify_correlation_cluster_preregistration,
    verify_correlation_matrix_contract,
)


COMPLETED_PRICE_INPUT_SCHEMA_VERSION = "strategy-correlation-completed-price-input-v1"
CORRELATION_MATRIX_REPLAY_SCHEMA_VERSION = "strategy-correlation-matrix-replay-v1"
REPLAYED_CLUSTER_GATE_SCHEMA_VERSION = "strategy-correlation-replayed-gate-v1"
RETURN_METHOD = "SIMPLE_CLOSE_TO_CLOSE_RETURN"
REQUIRED_PRICE_ROWS = LOOKBACK_OBSERVATIONS + 1
REPLAY_SCOPE = "LOCAL_FROZEN_COMPLETED_DAILY_CLOSE_REPLAY_NOT_EXTERNAL_AUTHENTICITY"

_PERMISSIONS = {"paper_authorized": False, "live_order_allowed": False}
_SYNTHETIC_SOURCE_TOKENS = ("synthetic", "preview_seed", "offline-seed")


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _finite_positive(value: Any) -> float:
    if type(value) not in {int, float}:
        raise ValueError("correlation_price_not_native_number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("correlation_price_not_finite_positive")
    return result


def _clean_symbol(value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError("correlation_symbol_invalid")
    return value.strip().upper()


def _clean_identity(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise ValueError(f"correlation_{label}_invalid")
    return value


def _iso_date(value: Any) -> str:
    if type(value) is not str or len(value.strip()) < 10:
        raise ValueError("correlation_date_invalid")
    text = value.strip()[:10]
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("correlation_date_invalid") from exc
    return parsed.isoformat()


def _verification(blockers: list[str]) -> dict[str, Any]:
    unique = list(dict.fromkeys(blockers))
    return {"status": "BLOCK" if unique else "PASS", "blockers": unique}


def build_correlation_completed_price_input(
    payloads: dict[str, dict[str, Any]],
    manifests: list[dict[str, Any]],
    preregistration: dict[str, Any],
    *,
    cutoff_date: str,
    selection_alignment_input_hash: str,
) -> dict[str, Any]:
    if verify_correlation_cluster_preregistration(preregistration)["status"] != "PASS":
        raise ValueError("correlation_preregistration_invalid")
    if type(payloads) is not dict or type(manifests) is not list:
        raise ValueError("correlation_source_container_invalid")
    if authority_violations(payloads) or authority_violations(manifests):
        raise ValueError("correlation_source_authority_invalid")
    cutoff = _iso_date(cutoff_date)
    if cutoff != cutoff_date or not _valid_sha256(selection_alignment_input_hash):
        raise ValueError("correlation_source_binding_invalid")

    manifest_by_symbol: dict[str, dict[str, Any]] = {}
    for manifest in manifests:
        if type(manifest) is not dict:
            raise ValueError("correlation_manifest_invalid")
        symbol = _clean_symbol(manifest.get("symbol"))
        if symbol in manifest_by_symbol or manifest.get("role") != "SELECTION":
            raise ValueError("correlation_manifest_identity_invalid")
        if str(manifest.get("timeframe") or "").strip().upper() != "1D":
            raise ValueError("correlation_manifest_timeframe_invalid")
        source = str(manifest.get("source") or "").strip()
        if not source or any(token in source.lower() for token in _SYNTHETIC_SOURCE_TOKENS):
            raise ValueError("correlation_manifest_source_invalid")
        if not _valid_sha256(manifest.get("data_hash")):
            raise ValueError("correlation_manifest_data_hash_invalid")
        manifest_by_symbol[symbol] = manifest

    expected_symbols = preregistration["symbols"]
    normalized_payloads: dict[str, dict[str, Any]] = {}
    for raw_symbol, payload in payloads.items():
        symbol = _clean_symbol(raw_symbol)
        if symbol in normalized_payloads or type(payload) is not dict:
            raise ValueError("correlation_payload_identity_invalid")
        normalized_payloads[symbol] = payload
    if set(normalized_payloads) != set(expected_symbols) or set(manifest_by_symbol) != set(expected_symbols):
        raise ValueError("correlation_source_coverage_invalid")

    datasets: list[dict[str, Any]] = []
    for symbol in sorted(expected_symbols):
        payload = normalized_payloads[symbol]
        manifest = manifest_by_symbol[symbol]
        rows = payload.get("rows")
        if type(rows) is not list or type(manifest.get("row_count")) is not int:
            raise ValueError("correlation_source_rows_invalid")
        if manifest["row_count"] != len(rows):
            raise ValueError("correlation_manifest_row_count_mismatch")
        source = str(payload.get("source") or "").strip()
        if source != str(manifest.get("source") or "").strip():
            raise ValueError("correlation_source_manifest_mismatch")

        completed: dict[str, float] = {}
        for raw_row in rows:
            if type(raw_row) is not dict:
                raise ValueError("correlation_source_row_invalid")
            if not candle_is_complete(raw_row, default_if_missing=False):
                continue
            trading_date = _iso_date(raw_row.get("date"))
            if trading_date > cutoff:
                continue
            if trading_date in completed:
                raise ValueError("correlation_source_duplicate_date")
            completed[trading_date] = _finite_positive(raw_row.get("close"))
        selected = sorted(completed.items())[-REQUIRED_PRICE_ROWS:]
        if len(selected) != REQUIRED_PRICE_ROWS:
            raise ValueError("correlation_completed_price_rows_insufficient")
        price_rows = [
            {"date": trading_date, "close": float(close), "complete": True}
            for trading_date, close in selected
        ]
        datasets.append({
            "role": "SELECTION",
            "symbol": symbol,
            "timeframe": "1D",
            "source": source,
            "dataset_data_hash": manifest["data_hash"],
            "dataset_manifest_hash": _canonical_hash(manifest),
            "manifest_row_count": manifest["row_count"],
            "price_rows": price_rows,
            "price_row_count": len(price_rows),
            "first_date": price_rows[0]["date"],
            "last_date": price_rows[-1]["date"],
        })

    body = {
        "schema_version": COMPLETED_PRICE_INPUT_SCHEMA_VERSION,
        "cutoff_date": cutoff,
        "return_method": RETURN_METHOD,
        "lookback_observations": LOOKBACK_OBSERVATIONS,
        "required_price_rows": REQUIRED_PRICE_ROWS,
        "selection_alignment_input_hash": selection_alignment_input_hash,
        "preregistration_hash": preregistration["preregistration_hash"],
        "datasets": datasets,
        "dataset_count": len(datasets),
        "replay_scope": REPLAY_SCOPE,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "input_hash": _canonical_hash(body)}


def verify_correlation_completed_price_input(
    document: Any,
    *,
    preregistration: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["correlation_completed_price_input_invalid"])
    if authority_violations(document):
        blockers.append("execution_authority_invalid")
    expected_keys = {
        "schema_version", "cutoff_date", "return_method", "lookback_observations",
        "required_price_rows", "selection_alignment_input_hash", "preregistration_hash",
        "datasets", "dataset_count", "replay_scope", "current_writer_activation_allowed",
        "current_admission_allowed", "permissions", "input_hash",
    }
    if set(document) != expected_keys:
        blockers.append("correlation_completed_price_input_invalid")
        return _verification(blockers)
    prereg_check = verify_correlation_cluster_preregistration(preregistration)
    if prereg_check["status"] != "PASS":
        blockers.append("correlation_preregistration_invalid")
        return _verification(blockers)
    try:
        cutoff = _iso_date(document["cutoff_date"])
    except (TypeError, ValueError):
        cutoff = ""
        blockers.append("correlation_cutoff_invalid")
    if (
        document["schema_version"] != COMPLETED_PRICE_INPUT_SCHEMA_VERSION
        or document["cutoff_date"] != cutoff
        or document["return_method"] != RETURN_METHOD
        or document["lookback_observations"] != LOOKBACK_OBSERVATIONS
        or document["required_price_rows"] != REQUIRED_PRICE_ROWS
        or not _valid_sha256(document["selection_alignment_input_hash"])
        or document["preregistration_hash"] != preregistration["preregistration_hash"]
        or document["replay_scope"] != REPLAY_SCOPE
        or document["current_writer_activation_allowed"] is not False
        or document["current_admission_allowed"] is not False
        or document["permissions"] != _PERMISSIONS
    ):
        blockers.append("correlation_completed_price_contract_mismatch")

    datasets = document["datasets"]
    seen: list[str] = []
    if type(datasets) is not list:
        blockers.append("correlation_completed_price_datasets_invalid")
    else:
        for dataset in datasets:
            if type(dataset) is not dict or set(dataset) != {
                "role", "symbol", "timeframe", "source", "dataset_data_hash",
                "dataset_manifest_hash", "manifest_row_count", "price_rows",
                "price_row_count", "first_date", "last_date",
            }:
                blockers.append("correlation_completed_price_dataset_invalid")
                continue
            try:
                symbol = _clean_symbol(dataset["symbol"])
            except ValueError:
                blockers.append("correlation_completed_price_dataset_invalid")
                continue
            seen.append(symbol)
            source = dataset["source"]
            rows = dataset["price_rows"]
            if (
                dataset["role"] != "SELECTION"
                or dataset["symbol"] != symbol
                or dataset["timeframe"] != "1D"
                or type(source) is not str
                or not source.strip()
                or any(token in source.lower() for token in _SYNTHETIC_SOURCE_TOKENS)
                or not _valid_sha256(dataset["dataset_data_hash"])
                or not _valid_sha256(dataset["dataset_manifest_hash"])
                or type(dataset["manifest_row_count"]) is not int
                or dataset["manifest_row_count"] < REQUIRED_PRICE_ROWS
                or type(rows) is not list
                or len(rows) != REQUIRED_PRICE_ROWS
                or dataset["price_row_count"] != REQUIRED_PRICE_ROWS
            ):
                blockers.append("correlation_completed_price_dataset_invalid")
                continue
            observed_dates: list[str] = []
            for row in rows:
                if type(row) is not dict or set(row) != {"date", "close", "complete"}:
                    blockers.append("correlation_completed_price_row_invalid")
                    continue
                try:
                    row_date = _iso_date(row["date"])
                    close = _finite_positive(row["close"])
                except (TypeError, ValueError):
                    blockers.append("correlation_completed_price_row_invalid")
                    continue
                if row["date"] != row_date or type(row["close"]) is not float or row["close"] != close or row["complete"] is not True:
                    blockers.append("correlation_completed_price_row_invalid")
                observed_dates.append(row_date)
            if (
                observed_dates != sorted(set(observed_dates))
                or (observed_dates and observed_dates[-1] > cutoff)
                or dataset["first_date"] != (observed_dates[0] if observed_dates else "")
                or dataset["last_date"] != (observed_dates[-1] if observed_dates else "")
            ):
                blockers.append("correlation_completed_price_date_topology_invalid")
    if (
        seen != sorted(preregistration["symbols"])
        or len(set(seen)) != len(seen)
        or document["dataset_count"] != len(preregistration["symbols"])
    ):
        blockers.append("correlation_completed_price_coverage_invalid")
    body = {key: value for key, value in document.items() if key != "input_hash"}
    try:
        if not _valid_sha256(document["input_hash"]) or document["input_hash"] != _canonical_hash(body):
            blockers.append("correlation_completed_price_hash_invalid")
    except (MemoryError, TypeError, ValueError):
        blockers.append("correlation_completed_price_hash_invalid")
    return _verification(blockers)


def _returns_by_symbol(document: dict[str, Any]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for dataset in document["datasets"]:
        returns: dict[str, float] = {}
        rows = dataset["price_rows"]
        for previous, current in zip(rows, rows[1:]):
            value = current["close"] / previous["close"] - 1.0
            if not math.isfinite(value):
                raise ValueError("correlation_return_nonfinite")
            returns[current["date"]] = value
        result[dataset["symbol"]] = returns
    return result


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation_pair_observations_insufficient")
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    left_delta = [value - left_mean for value in left]
    right_delta = [value - right_mean for value in right]
    numerator = math.fsum(a * b for a, b in zip(left_delta, right_delta))
    left_energy = math.fsum(value * value for value in left_delta)
    right_energy = math.fsum(value * value for value in right_delta)
    denominator = math.sqrt(left_energy * right_energy)
    if not math.isfinite(denominator) or denominator <= 0:
        raise ValueError("correlation_pair_variance_zero")
    result = numerator / denominator
    if not math.isfinite(result) or abs(result) > 1.000000000001:
        raise ValueError("correlation_pair_result_invalid")
    return max(-1.0, min(1.0, result))


def _matrix_from_verified_input(document: dict[str, Any]) -> dict[str, Any]:
    returns = _returns_by_symbol(document)
    correlations: dict[tuple[str, str], float] = {}
    overlaps: dict[tuple[str, str], int] = {}
    for left, right in combinations(sorted(returns), 2):
        dates = sorted(set(returns[left]).intersection(returns[right]))[-LOOKBACK_OBSERVATIONS:]
        correlations[(left, right)] = _pearson(
            [returns[left][item] for item in dates],
            [returns[right][item] for item in dates],
        )
        overlaps[(left, right)] = len(dates)
    return build_correlation_matrix_contract(
        sorted(returns),
        correlations,
        overlap_observations=overlaps,
    )


def build_correlation_matrix_replay(
    completed_price_input: dict[str, Any],
    preregistration: dict[str, Any],
) -> dict[str, Any]:
    input_check = verify_correlation_completed_price_input(
        completed_price_input,
        preregistration=preregistration,
    )
    if input_check["status"] != "PASS":
        raise ValueError("correlation_completed_price_input_invalid")
    matrix = _matrix_from_verified_input(completed_price_input)
    body = {
        "schema_version": CORRELATION_MATRIX_REPLAY_SCHEMA_VERSION,
        "status": "PASS",
        "replay_scope": REPLAY_SCOPE,
        "preregistration": deepcopy(preregistration),
        "completed_price_input": deepcopy(completed_price_input),
        "correlation_matrix": matrix,
        "pair_count": len(matrix["pairs"]),
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "replay_hash": _canonical_hash(body)}


def verify_correlation_matrix_replay(document: Any) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["correlation_matrix_replay_invalid"])
    if authority_violations(document):
        blockers.append("execution_authority_invalid")
    expected_keys = {
        "schema_version", "status", "replay_scope", "preregistration",
        "completed_price_input", "correlation_matrix", "pair_count",
        "current_writer_activation_allowed", "current_admission_allowed",
        "permissions", "replay_hash",
    }
    if set(document) != expected_keys:
        blockers.append("correlation_matrix_replay_invalid")
        return _verification(blockers)
    preregistration = document["preregistration"]
    completed_input = document["completed_price_input"]
    matrix = document["correlation_matrix"]
    prereg_check = verify_correlation_cluster_preregistration(preregistration)
    input_check = verify_correlation_completed_price_input(completed_input, preregistration=preregistration)
    expected_symbols = preregistration.get("symbols", []) if type(preregistration) is dict else []
    matrix_check = verify_correlation_matrix_contract(matrix, expected_symbols=expected_symbols)
    if prereg_check["status"] != "PASS":
        blockers.append("correlation_replay_preregistration_invalid")
    if input_check["status"] != "PASS":
        blockers.append("correlation_replay_input_invalid")
    if matrix_check["status"] != "PASS":
        blockers.append("correlation_replay_matrix_invalid")
    if not blockers:
        try:
            rebuilt_matrix = _matrix_from_verified_input(completed_input)
        except (ArithmeticError, MemoryError, TypeError, ValueError):
            rebuilt_matrix = {}
            blockers.append("correlation_replay_recompute_failed")
        if matrix != rebuilt_matrix:
            blockers.append("correlation_replay_semantic_mismatch")
    if (
        document["schema_version"] != CORRELATION_MATRIX_REPLAY_SCHEMA_VERSION
        or document["status"] != "PASS"
        or document["replay_scope"] != REPLAY_SCOPE
        or document["pair_count"] != (len(matrix.get("pairs", [])) if type(matrix) is dict else -1)
        or document["current_writer_activation_allowed"] is not False
        or document["current_admission_allowed"] is not False
        or document["permissions"] != _PERMISSIONS
    ):
        blockers.append("correlation_matrix_replay_contract_mismatch")
    body = {key: value for key, value in document.items() if key != "replay_hash"}
    try:
        if not _valid_sha256(document["replay_hash"]) or document["replay_hash"] != _canonical_hash(body):
            blockers.append("correlation_matrix_replay_hash_invalid")
    except (MemoryError, TypeError, ValueError):
        blockers.append("correlation_matrix_replay_hash_invalid")
    return _verification(blockers)


def build_replayed_correlation_cluster_gate(
    matrix_replay: dict[str, Any],
    selection_cells: list[dict[str, Any]],
    *,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> dict[str, Any]:
    if verify_correlation_matrix_replay(matrix_replay)["status"] != "PASS":
        raise ValueError("correlation_matrix_replay_invalid")
    _clean_identity(strategy_id, "strategy_id")
    _clean_identity(variant_id, "variant_id")
    if type(lane) is not str or lane not in LANES or type(selection_cells) is not list:
        raise ValueError("correlation_gate_identity_invalid")
    cells = deepcopy(selection_cells)
    gate = evaluate_correlation_cluster_gate(
        matrix_replay["preregistration"],
        matrix_replay["correlation_matrix"],
        cells,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    body = {
        "schema_version": REPLAYED_CLUSTER_GATE_SCHEMA_VERSION,
        "status": gate["status"],
        "source_replay_status": "PASS",
        "matrix_replay": deepcopy(matrix_replay),
        "selection_cells": cells,
        "strategy_id": strategy_id,
        "variant_id": variant_id,
        "lane": lane,
        "gate": gate,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "requires_new_report_schema": True,
        "permissions": dict(_PERMISSIONS),
    }
    return {**body, "evaluation_hash": _canonical_hash(body)}


def verify_replayed_correlation_cluster_gate(document: Any) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(["replayed_correlation_gate_invalid"])
    if authority_violations(document):
        blockers.append("execution_authority_invalid")
    expected_keys = {
        "schema_version", "status", "source_replay_status", "matrix_replay",
        "selection_cells", "strategy_id", "variant_id", "lane", "gate",
        "current_writer_activation_allowed", "current_admission_allowed",
        "requires_new_report_schema", "permissions", "evaluation_hash",
    }
    if set(document) != expected_keys:
        blockers.append("replayed_correlation_gate_invalid")
        return _verification(blockers)
    try:
        rebuilt = build_replayed_correlation_cluster_gate(
            document["matrix_replay"],
            document["selection_cells"],
            strategy_id=document["strategy_id"],
            variant_id=document["variant_id"],
            lane=document["lane"],
        )
    except (ArithmeticError, MemoryError, TypeError, ValueError):
        rebuilt = {}
        blockers.append("replayed_correlation_gate_rebuild_failed")
    if document != rebuilt:
        blockers.append("replayed_correlation_gate_semantic_mismatch")
    if (
        document["schema_version"] != REPLAYED_CLUSTER_GATE_SCHEMA_VERSION
        or document["source_replay_status"] != "PASS"
        or document["current_writer_activation_allowed"] is not False
        or document["current_admission_allowed"] is not False
        or document["requires_new_report_schema"] is not True
        or document["permissions"] != _PERMISSIONS
    ):
        blockers.append("replayed_correlation_gate_contract_mismatch")
    return _verification(blockers)


__all__ = [
    "COMPLETED_PRICE_INPUT_SCHEMA_VERSION",
    "CORRELATION_MATRIX_REPLAY_SCHEMA_VERSION",
    "REPLAYED_CLUSTER_GATE_SCHEMA_VERSION",
    "REPLAY_SCOPE",
    "REQUIRED_PRICE_ROWS",
    "RETURN_METHOD",
    "build_correlation_completed_price_input",
    "build_correlation_matrix_replay",
    "build_replayed_correlation_cluster_gate",
    "verify_correlation_completed_price_input",
    "verify_correlation_matrix_replay",
    "verify_replayed_correlation_cluster_gate",
]
