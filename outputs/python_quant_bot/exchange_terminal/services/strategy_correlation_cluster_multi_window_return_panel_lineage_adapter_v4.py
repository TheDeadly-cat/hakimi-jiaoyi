"""Raw return-panel lineage adapter for the dynamic multi-window consumer.

The adapter rebuilds each source-v2 correlation matrix from one bounded common
observation panel, verifies the exact consumer-v3 document, and emits only
bounded lineage summaries. It is pure, unmounted, and research-only.
"""

from __future__ import annotations

import copy
from datetime import date
import hmac
from itertools import combinations
import math
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_independent_ticket_consumer_v3
    as consumer_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_window_source_v2 as source_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PANEL_SCHEMA_VERSION = "strategy-correlation-common-return-panel-v1"
LINEAGE_PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-return-panel-lineage-"
    "preregistration-v4"
)
ADAPTER_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-return-panel-lineage-adapter-v4"
)
PANEL_VERIFICATION_SCHEMA_VERSION = f"{PANEL_SCHEMA_VERSION}-verification-v1"
LINEAGE_PREREGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    f"{LINEAGE_PREREGISTRATION_SCHEMA_VERSION}-verification-v1"
)
ADAPTER_VERIFICATION_SCHEMA_VERSION = f"{ADAPTER_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-correlation-cluster-multi-window-return-panel-lineage-v4-lock-1"
)
TIMEFRAME = "1d"
CORRELATION_METHOD = "PEARSON_COMPLETED_DAILY_RETURNS_COMMON_LAST_N_ROWS"
CORRELATION_DECIMALS = 12
MAXIMUM_PANEL_ROWS = 5000
MAXIMUM_SYMBOL_COUNT = 128

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ROW_KEYS = {"date", "returns"}


class MultiWindowReturnPanelLineageContractError(ValueError):
    """Raised when the panel or lineage contract is not canonical."""


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


def _symbol(value: Any) -> str:
    if type(value) is not str or not value.strip():
        raise MultiWindowReturnPanelLineageContractError("symbol is invalid")
    return value.strip().upper()


def _date(value: Any, label: str) -> str:
    if type(value) is not str or _DATE_RE.fullmatch(value) is None:
        raise MultiWindowReturnPanelLineageContractError(f"{label} is invalid")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise MultiWindowReturnPanelLineageContractError(
            f"{label} is invalid"
        ) from exc
    if parsed.isoformat() != value:
        raise MultiWindowReturnPanelLineageContractError(f"{label} is invalid")
    return value


def _finite_return(value: Any) -> float:
    if type(value) not in {int, float} or not math.isfinite(float(value)):
        raise MultiWindowReturnPanelLineageContractError(
            "return values must be finite native numbers"
        )
    return float(value)


def build_common_return_panel_v1(
    *,
    symbols: Any,
    rows: Any,
    timeframe: Any,
    cutoff_date: Any,
) -> dict[str, Any]:
    if type(symbols) is not list:
        raise MultiWindowReturnPanelLineageContractError("symbols must be a list")
    clean_symbols = sorted(_symbol(symbol) for symbol in symbols)
    if (
        len(clean_symbols) < 2
        or len(clean_symbols) > MAXIMUM_SYMBOL_COUNT
        or len(set(clean_symbols)) != len(clean_symbols)
    ):
        raise MultiWindowReturnPanelLineageContractError(
            "symbols must be a bounded unique universe"
        )
    if timeframe != TIMEFRAME or type(timeframe) is not str:
        raise MultiWindowReturnPanelLineageContractError("timeframe is invalid")
    clean_cutoff = _date(cutoff_date, "cutoff_date")
    if (
        type(rows) is not list
        or not rows
        or len(rows) > MAXIMUM_PANEL_ROWS
    ):
        raise MultiWindowReturnPanelLineageContractError(
            "rows must be a bounded non-empty list"
        )
    normalized_rows: list[dict[str, Any]] = []
    previous_date = ""
    for row in rows:
        if type(row) is not dict or set(row) != _ROW_KEYS:
            raise MultiWindowReturnPanelLineageContractError(
                "return row shape is invalid"
            )
        row_date = _date(row["date"], "row date")
        if row_date <= previous_date or row_date > clean_cutoff:
            raise MultiWindowReturnPanelLineageContractError(
                "return row dates must be strictly increasing through cutoff"
            )
        returns = row["returns"]
        if type(returns) is not dict or set(returns) != set(clean_symbols):
            raise MultiWindowReturnPanelLineageContractError(
                "every row must contain the exact common symbol membership"
            )
        normalized_rows.append(
            {
                "date": row_date,
                "returns": {
                    symbol: _finite_return(returns[symbol])
                    for symbol in clean_symbols
                },
            }
        )
        previous_date = row_date
    if normalized_rows[-1]["date"] != clean_cutoff:
        raise MultiWindowReturnPanelLineageContractError(
            "the final return row must equal cutoff_date"
        )
    body = {
        "schema_version": PANEL_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS",
        "timeframe": TIMEFRAME,
        "cutoff_date": clean_cutoff,
        "symbols": clean_symbols,
        "row_count": len(normalized_rows),
        "rows": normalized_rows,
        "facts": {
            "common_observation_membership_exact": True,
            "strictly_increasing_dates": True,
            "future_rows_after_cutoff_present": False,
            "runtime_sources_accessed": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(body, "panel_hash")


def verify_common_return_panel_v1(
    document: Any,
    *,
    expected_panel_hash: Any,
    expected_symbols: Any,
    expected_timeframe: Any,
    expected_cutoff_date: Any,
    minimum_row_count: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(
            PANEL_VERIFICATION_SCHEMA_VERSION,
            ["return_panel_object_required"],
            panel_hash=None,
        )
    if not _same_hash(document.get("panel_hash"), expected_panel_hash):
        blockers.append("return_panel_expected_hash_mismatch")
    if (
        type(minimum_row_count) is not int
        or isinstance(minimum_row_count, bool)
        or minimum_row_count < 1
    ):
        blockers.append("return_panel_minimum_row_count_invalid")
    try:
        clean_expected_symbols = sorted(_symbol(symbol) for symbol in expected_symbols)
        rebuilt = build_common_return_panel_v1(
            symbols=document.get("symbols"),
            rows=document.get("rows"),
            timeframe=document.get("timeframe"),
            cutoff_date=document.get("cutoff_date"),
        )
        if (
            clean_expected_symbols != document.get("symbols")
            or expected_timeframe != document.get("timeframe")
            or expected_cutoff_date != document.get("cutoff_date")
            or document.get("row_count", 0) < minimum_row_count
            or not strict_json_contract_equal(document, rebuilt)
        ):
            blockers.append("return_panel_contract_invalid")
    except Exception:
        blockers.append("return_panel_contract_invalid")
    return _verification(
        PANEL_VERIFICATION_SCHEMA_VERSION,
        blockers,
        panel_hash=document.get("panel_hash") if not blockers else None,
        row_count=document.get("row_count") if not blockers else None,
    )


def _source_map_exact(
    consumer_preregistration: Any,
    source_preregistrations: Any,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    if type(consumer_preregistration) is not dict:
        raise MultiWindowReturnPanelLineageContractError(
            "consumer preregistration is invalid"
        )
    consumer_hash = consumer_preregistration.get(
        "consumer_preregistration_v3_hash"
    )
    consumer_receipt = (
        consumer_v3.verify_multi_window_independent_ticket_consumer_preregistration_v3(
            consumer_preregistration,
            expected_consumer_preregistration_v3_hash=consumer_hash,
        )
    )
    if consumer_receipt["status"] != "PASS":
        raise MultiWindowReturnPanelLineageContractError(
            "consumer preregistration is invalid"
        )
    bindings = consumer_preregistration["window_bindings"]
    expected_ids = [binding["window_id"] for binding in bindings]
    if (
        type(source_preregistrations) is not dict
        or set(source_preregistrations) != set(expected_ids)
    ):
        raise MultiWindowReturnPanelLineageContractError(
            "source preregistration coverage is invalid"
        )
    source_map: dict[str, dict[str, Any]] = {}
    universes: list[tuple[str, ...]] = []
    for binding in bindings:
        window_id = binding["window_id"]
        source = source_preregistrations[window_id]
        expected_hash = binding["source_preregistration_v2_hash"]
        receipt = source_v2.verify_correlation_cluster_window_source_preregistration_v2(
            source,
            expected_preregistration_v2_hash=expected_hash,
        )
        if (
            receipt["status"] != "PASS"
            or source.get("window_id") != window_id
            or source.get("lookback_observations")
            != binding["lookback_observations"]
        ):
            raise MultiWindowReturnPanelLineageContractError(
                "source preregistration binding is invalid"
            )
        source_map[window_id] = source
        universes.append(tuple(source["symbols"]))
    if len(set(universes)) != 1:
        raise MultiWindowReturnPanelLineageContractError(
            "source symbol universes must be identical"
        )
    return bindings, source_map, list(universes[0])


def build_multi_window_return_panel_lineage_preregistration_v4(
    consumer_preregistration: Any,
    source_preregistrations: Any,
    *,
    expected_panel_hash: Any,
    timeframe: Any,
    cutoff_date: Any,
) -> dict[str, Any]:
    if not _is_hash(expected_panel_hash):
        raise MultiWindowReturnPanelLineageContractError(
            "expected_panel_hash is invalid"
        )
    if timeframe != TIMEFRAME or type(timeframe) is not str:
        raise MultiWindowReturnPanelLineageContractError("timeframe is invalid")
    clean_cutoff = _date(cutoff_date, "cutoff_date")
    bindings, _, symbols = _source_map_exact(
        consumer_preregistration,
        source_preregistrations,
    )
    body = {
        "schema_version": LINEAGE_PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_RESEARCH_ONLY",
        "consumer_preregistration_v3_hash": consumer_preregistration[
            "consumer_preregistration_v3_hash"
        ],
        "window_bindings": copy.deepcopy(bindings),
        "panel_schema_version": PANEL_SCHEMA_VERSION,
        "expected_panel_hash": expected_panel_hash,
        "timeframe": TIMEFRAME,
        "cutoff_date": clean_cutoff,
        "symbols": symbols,
        "minimum_panel_row_count": max(
            binding["lookback_observations"] for binding in bindings
        ),
        "correlation_method": CORRELATION_METHOD,
        "correlation_decimals": CORRELATION_DECIMALS,
        "common_observation_policy": (
            "EXACT_COMMON_SYMBOL_MEMBERSHIP_AND_LAST_N_PANEL_ROWS"
        ),
        "facts": {
            "structural_preregistration_only": True,
            "chronology_independently_proven": False,
            "panel_rows_observed_by_builder": False,
            "raw_rows_embedded": False,
            "current_activated": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        body,
        "lineage_preregistration_v4_hash",
    )


def verify_multi_window_return_panel_lineage_preregistration_v4(
    document: Any,
    consumer_preregistration: Any,
    source_preregistrations: Any,
    *,
    expected_lineage_preregistration_v4_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(
            LINEAGE_PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
            ["return_panel_lineage_preregistration_object_required"],
            lineage_preregistration_v4_hash=None,
        )
    if not _same_hash(
        document.get("lineage_preregistration_v4_hash"),
        expected_lineage_preregistration_v4_hash,
    ):
        blockers.append("return_panel_lineage_preregistration_hash_mismatch")
    try:
        rebuilt = build_multi_window_return_panel_lineage_preregistration_v4(
            consumer_preregistration,
            source_preregistrations,
            expected_panel_hash=document.get("expected_panel_hash"),
            timeframe=document.get("timeframe"),
            cutoff_date=document.get("cutoff_date"),
        )
        if not strict_json_contract_equal(document, rebuilt):
            blockers.append("return_panel_lineage_preregistration_contract_invalid")
    except Exception:
        blockers.append("return_panel_lineage_preregistration_contract_invalid")
    return _verification(
        LINEAGE_PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        blockers,
        lineage_preregistration_v4_hash=(
            document.get("lineage_preregistration_v4_hash")
            if not blockers
            else None
        ),
    )


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise MultiWindowReturnPanelLineageContractError(
            "correlation vectors are invalid"
        )
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    numerator = math.fsum(
        a * b for a, b in zip(left_centered, right_centered, strict=True)
    )
    denominator = math.sqrt(
        math.fsum(value * value for value in left_centered)
        * math.fsum(value * value for value in right_centered)
    )
    if not math.isfinite(denominator) or denominator <= 0:
        raise MultiWindowReturnPanelLineageContractError(
            "correlation variance must be positive"
        )
    correlation = max(-1.0, min(1.0, numerator / denominator))
    rounded = round(correlation, CORRELATION_DECIMALS)
    return 0.0 if rounded == 0.0 else rounded


def derive_multi_window_matrices_from_return_panel_v4(
    lineage_preregistration: Any,
    consumer_preregistration: Any,
    source_preregistrations: Any,
    panel: Any,
) -> dict[str, dict[str, Any]]:
    if type(lineage_preregistration) is not dict:
        raise MultiWindowReturnPanelLineageContractError(
            "lineage preregistration is invalid"
        )
    lineage_hash = lineage_preregistration.get(
        "lineage_preregistration_v4_hash"
    )
    lineage_receipt = verify_multi_window_return_panel_lineage_preregistration_v4(
        lineage_preregistration,
        consumer_preregistration,
        source_preregistrations,
        expected_lineage_preregistration_v4_hash=lineage_hash,
    )
    if lineage_receipt["status"] != "PASS":
        raise MultiWindowReturnPanelLineageContractError(
            "lineage preregistration is invalid"
        )
    panel_receipt = verify_common_return_panel_v1(
        panel,
        expected_panel_hash=lineage_preregistration["expected_panel_hash"],
        expected_symbols=lineage_preregistration["symbols"],
        expected_timeframe=lineage_preregistration["timeframe"],
        expected_cutoff_date=lineage_preregistration["cutoff_date"],
        minimum_row_count=lineage_preregistration["minimum_panel_row_count"],
    )
    if panel_receipt["status"] != "PASS":
        raise MultiWindowReturnPanelLineageContractError("return panel is invalid")
    bindings, source_map, symbols = _source_map_exact(
        consumer_preregistration,
        source_preregistrations,
    )
    rows = panel["rows"]
    matrices: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        window_id = binding["window_id"]
        lookback = binding["lookback_observations"]
        window_rows = rows[-lookback:]
        correlations = {
            (left, right): _pearson(
                [row["returns"][left] for row in window_rows],
                [row["returns"][right] for row in window_rows],
            )
            for left, right in combinations(symbols, 2)
        }
        matrices[window_id] = source_v2.build_correlation_cluster_window_matrix_v2(
            source_map[window_id],
            correlations,
            overlap_observations=lookback,
        )
    return matrices


def _seal_adapter(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "adapter_v4_hash")


def evaluate_multi_window_return_panel_lineage_adapter_v4(
    lineage_preregistration: Any,
    consumer_preregistration: Any,
    source_preregistrations: Any,
    panel: Any,
    consumer_document: Any,
    window_inputs: Any,
    *,
    expected_lineage_preregistration_v4_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "decision": "BLOCK_RETURN_PANEL_LINEAGE_UNVERIFIED",
        "lineage_preregistration_v4_hash": None,
        "panel_hash": None,
        "consumer_v3_hash": None,
        "first_blocking_tier": "LINEAGE",
        "tiers": [],
        "blockers": [],
        "window_lineage_summaries": [],
        "summary": None,
        "facts": {
            "raw_return_rows_recomputed": False,
            "common_observation_membership_exact": False,
            "all_window_matrices_exactly_derived": False,
            "consumer_v3_exactly_verified": False,
            "raw_rows_embedded": False,
            "source_documents_embedded": False,
            "current_activated": False,
            "runtime_sources_accessed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }
    lineage_blockers: list[str] = []
    lineage_receipt = verify_multi_window_return_panel_lineage_preregistration_v4(
        lineage_preregistration,
        consumer_preregistration,
        source_preregistrations,
        expected_lineage_preregistration_v4_hash=(
            expected_lineage_preregistration_v4_hash
        ),
    )
    if lineage_receipt["status"] != "PASS":
        lineage_blockers.append("return_panel_lineage_preregistration_invalid")
    try:
        expected_matrices = derive_multi_window_matrices_from_return_panel_v4(
            lineage_preregistration,
            consumer_preregistration,
            source_preregistrations,
            panel,
        )
    except Exception:
        expected_matrices = {}
        lineage_blockers.append("return_panel_matrix_derivation_failed")
    bindings = (
        consumer_preregistration.get("window_bindings")
        if type(consumer_preregistration) is dict
        else []
    )
    expected_ids = [
        binding.get("window_id") for binding in bindings if type(binding) is dict
    ]
    if (
        type(window_inputs) is not dict
        or set(window_inputs) != set(expected_ids)
        or set(expected_matrices) != set(expected_ids)
    ):
        lineage_blockers.append("return_panel_window_coverage_invalid")
    if not lineage_blockers:
        for window_id in expected_ids:
            item = window_inputs[window_id]
            source = source_preregistrations[window_id]
            if (
                type(item) is not dict
                or not strict_json_contract_equal(
                    item.get("source_preregistration"),
                    source,
                )
                or not strict_json_contract_equal(
                    item.get("matrix"),
                    expected_matrices[window_id],
                )
            ):
                lineage_blockers.append(
                    f"return_panel_window_matrix_mismatch:{window_id}"
                )
    consumer_receipt = consumer_v3.verify_multi_window_independent_ticket_consumer_v3(
        consumer_document,
        consumer_preregistration,
        window_inputs,
        expected_consumer_preregistration_v3_hash=(
            consumer_preregistration.get("consumer_preregistration_v3_hash")
            if type(consumer_preregistration) is dict
            else None
        ),
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
    )
    if (
        consumer_receipt.get("status") != "PASS"
        or consumer_receipt.get("consumer_status") not in {"PASS", "BLOCK"}
    ):
        lineage_blockers.append("consumer_v3_exact_verification_failed")
    if lineage_blockers:
        base["blockers"] = sorted(set(lineage_blockers))
        base["tiers"] = [
            {"tier_id": "LINEAGE", "status": "BLOCK", "blockers": base["blockers"]},
            {"tier_id": "CONSUMER", "status": "NOT_EVALUATED", "blockers": []},
        ]
        return _seal_adapter(base)

    base["lineage_preregistration_v4_hash"] = lineage_preregistration[
        "lineage_preregistration_v4_hash"
    ]
    base["panel_hash"] = panel["panel_hash"]
    base["consumer_v3_hash"] = consumer_document["consumer_v3_hash"]
    base["facts"].update(
        {
            "raw_return_rows_recomputed": True,
            "common_observation_membership_exact": True,
            "all_window_matrices_exactly_derived": True,
            "consumer_v3_exactly_verified": True,
        }
    )
    rows = panel["rows"]
    summaries = []
    for binding in bindings:
        lookback = binding["lookback_observations"]
        summaries.append(
            {
                "window_id": binding["window_id"],
                "lookback_observations": lookback,
                "common_observation_count": lookback,
                "first_observation_date": rows[-lookback]["date"],
                "last_observation_date": rows[-1]["date"],
                "matrix_v2_hash": expected_matrices[binding["window_id"]][
                    "matrix_v2_hash"
                ],
            }
        )
    base["window_lineage_summaries"] = summaries
    base["summary"] = {
        "panel_row_count": panel["row_count"],
        "panel_symbol_count": len(panel["symbols"]),
        "verified_window_matrix_count": len(summaries),
        "cutoff_date": panel["cutoff_date"],
        "timeframe": panel["timeframe"],
        "consumer_status": consumer_receipt["consumer_status"],
        "conservative_effective_independent_ticket_count": consumer_document[
            "summary"
        ]["conservative_effective_independent_ticket_count"],
    }
    consumer_blocked = consumer_receipt["consumer_status"] == "BLOCK"
    base.update(
        {
            "status": "BLOCK" if consumer_blocked else "PASS",
            "decision": (
                "BLOCK_RETURN_PANEL_LINEAGE_CONSUMER_V4"
                if consumer_blocked
                else "PASS_RETURN_PANEL_LINEAGE_RESEARCH_ADAPTER_V4"
            ),
            "first_blocking_tier": "CONSUMER" if consumer_blocked else None,
            "blockers": ["consumer_v3_blocked"] if consumer_blocked else [],
            "tiers": [
                {"tier_id": "LINEAGE", "status": "PASS", "blockers": []},
                {
                    "tier_id": "CONSUMER",
                    "status": "BLOCK" if consumer_blocked else "PASS",
                    "blockers": ["consumer_v3_blocked"] if consumer_blocked else [],
                },
            ],
        }
    )
    return _seal_adapter(base)


def verify_multi_window_return_panel_lineage_adapter_v4(
    document: Any,
    lineage_preregistration: Any,
    consumer_preregistration: Any,
    source_preregistrations: Any,
    panel: Any,
    consumer_document: Any,
    window_inputs: Any,
    *,
    expected_lineage_preregistration_v4_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_multi_window_return_panel_lineage_adapter_v4(
            lineage_preregistration,
            consumer_preregistration,
            source_preregistrations,
            panel,
            consumer_document,
            window_inputs,
            expected_lineage_preregistration_v4_hash=(
                expected_lineage_preregistration_v4_hash
            ),
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
        exact = type(document) is dict and strict_json_contract_equal(document, expected)
    except Exception:
        expected = {}
        exact = False
    return _verification(
        ADAPTER_VERIFICATION_SCHEMA_VERSION,
        [] if exact else ["return_panel_lineage_adapter_v4_contract_invalid"],
        adapter_status=expected.get("status") if exact else "UNKNOWN",
        adapter_decision=expected.get("decision") if exact else "UNKNOWN",
        adapter_v4_hash=expected.get("adapter_v4_hash") if exact else None,
    )


__all__ = [
    "ADAPTER_SCHEMA_VERSION",
    "LINEAGE_PREREGISTRATION_SCHEMA_VERSION",
    "MultiWindowReturnPanelLineageContractError",
    "PANEL_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_common_return_panel_v1",
    "build_multi_window_return_panel_lineage_preregistration_v4",
    "derive_multi_window_matrices_from_return_panel_v4",
    "evaluate_multi_window_return_panel_lineage_adapter_v4",
    "verify_common_return_panel_v1",
    "verify_multi_window_return_panel_lineage_adapter_v4",
    "verify_multi_window_return_panel_lineage_preregistration_v4",
]
