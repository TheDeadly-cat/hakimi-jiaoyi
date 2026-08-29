"""Exact multi-window consumer for dynamic correlation source-v2 gates.

This unmounted research consumer replaces mocked window receipts with exact
source-v2 preregistration, matrix, and gate verification.  It aggregates three
pre-registered windows conservatively and grants no runtime or trading authority.
"""

from __future__ import annotations

import copy
import hmac
import math
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_window_source_v2 as source_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-independent-ticket-"
    "consumer-preregistration-v3"
)
CONSUMER_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-independent-ticket-consumer-v3"
)
PREREGISTRATION_VERIFICATION_SCHEMA_VERSION = (
    f"{PREREGISTRATION_SCHEMA_VERSION}-verification-v1"
)
CONSUMER_VERIFICATION_SCHEMA_VERSION = f"{CONSUMER_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-correlation-cluster-multi-window-independent-ticket-"
    "consumer-v3-lock-1"
)
REQUIRED_WINDOW_COUNT = 3
WINDOW_AGGREGATION_POLICY = "ALL_EXACT_DYNAMIC_WINDOWS_MUST_PASS"
PARTITION_STABILITY_POLICY = "REQUIRE_IDENTICAL_EXACT_CLUSTER_PARTITION"
EFFECTIVE_TICKET_POLICY = "MINIMUM_EFFECTIVE_INDEPENDENT_TICKETS_ACROSS_WINDOWS"
LANES = frozenset({"RAW_EXCESS", "RISK_ADJUSTED"})

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOW_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_BINDING_KEYS = {
    "window_id",
    "lookback_observations",
    "source_preregistration_v2_hash",
}
_WINDOW_INPUT_KEYS = {
    "source_preregistration",
    "matrix",
    "selection_cells",
    "gate",
}


class MultiWindowIndependentTicketConsumerContractError(ValueError):
    """Raised when the v3 consumer preregistration is not canonical."""


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
        raise MultiWindowIndependentTicketConsumerContractError(
            f"{label} is invalid"
        )
    return value


def _validate_bindings(value: Any) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != REQUIRED_WINDOW_COUNT:
        raise MultiWindowIndependentTicketConsumerContractError(
            "exactly three window bindings are required"
        )
    normalized: list[dict[str, Any]] = []
    window_ids: set[str] = set()
    source_hashes: set[str] = set()
    previous_lookback = 0
    for item in value:
        if type(item) is not dict or set(item) != _BINDING_KEYS:
            raise MultiWindowIndependentTicketConsumerContractError(
                "window binding shape is invalid"
            )
        window_id = item["window_id"]
        lookback = item["lookback_observations"]
        source_hash = item["source_preregistration_v2_hash"]
        if type(window_id) is not str or _WINDOW_ID_RE.fullmatch(window_id) is None:
            raise MultiWindowIndependentTicketConsumerContractError(
                "window_id is invalid"
            )
        if window_id in window_ids:
            raise MultiWindowIndependentTicketConsumerContractError(
                "window_id must be unique"
            )
        if (
            type(lookback) is not int
            or isinstance(lookback, bool)
            or lookback < source_v2.MINIMUM_LOOKBACK_OBSERVATIONS
            or lookback > source_v2.MAXIMUM_LOOKBACK_OBSERVATIONS
            or lookback <= previous_lookback
        ):
            raise MultiWindowIndependentTicketConsumerContractError(
                "lookbacks must be strictly increasing native integers"
            )
        if not _is_hash(source_hash) or source_hash in source_hashes:
            raise MultiWindowIndependentTicketConsumerContractError(
                "source preregistration hashes must be unique SHA-256 values"
            )
        window_ids.add(window_id)
        source_hashes.add(source_hash)
        previous_lookback = lookback
        normalized.append(copy.deepcopy(item))
    return normalized


def build_multi_window_independent_ticket_consumer_preregistration_v3(
    window_bindings: Any,
) -> dict[str, Any]:
    bindings = _validate_bindings(window_bindings)
    body = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_RESEARCH_ONLY",
        "required_window_count": REQUIRED_WINDOW_COUNT,
        "window_aggregation_policy": WINDOW_AGGREGATION_POLICY,
        "partition_stability_policy": PARTITION_STABILITY_POLICY,
        "effective_ticket_policy": EFFECTIVE_TICKET_POLICY,
        "source_schema_version": source_v2.PREREGISTRATION_SCHEMA_VERSION,
        "source_static_fingerprint": source_v2.STATIC_FINGERPRINT,
        "window_bindings": bindings,
        "facts": {
            "structural_preregistration_only": True,
            "chronology_independently_proven": False,
            "window_results_observed_by_builder": False,
            "source_documents_embedded": False,
            "current_activated": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        body,
        "consumer_preregistration_v3_hash",
    )


def verify_multi_window_independent_ticket_consumer_preregistration_v3(
    document: Any,
    *,
    expected_consumer_preregistration_v3_hash: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if type(document) is not dict:
        return _verification(
            PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
            ["multi_window_consumer_preregistration_object_required"],
            consumer_preregistration_v3_hash=None,
        )
    if not _same_hash(
        document.get("consumer_preregistration_v3_hash"),
        expected_consumer_preregistration_v3_hash,
    ):
        blockers.append("multi_window_consumer_preregistration_hash_mismatch")
    try:
        rebuilt = build_multi_window_independent_ticket_consumer_preregistration_v3(
            document.get("window_bindings")
        )
        if not strict_json_contract_equal(document, rebuilt):
            blockers.append("multi_window_consumer_preregistration_contract_invalid")
    except Exception:
        blockers.append("multi_window_consumer_preregistration_contract_invalid")
    return _verification(
        PREREGISTRATION_VERIFICATION_SCHEMA_VERSION,
        blockers,
        consumer_preregistration_v3_hash=(
            document.get("consumer_preregistration_v3_hash")
            if not blockers
            else None
        ),
    )


def _partition_key(source_preregistration: dict[str, Any]) -> tuple[Any, ...]:
    clusters = source_preregistration.get("clusters")
    if type(clusters) is not list:
        raise MultiWindowIndependentTicketConsumerContractError(
            "source cluster partition is invalid"
        )
    result: list[tuple[str, tuple[str, ...]]] = []
    for cluster in clusters:
        if type(cluster) is not dict:
            raise MultiWindowIndependentTicketConsumerContractError(
                "source cluster partition is invalid"
            )
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if (
            type(cluster_id) is not str
            or type(members) is not list
            or any(type(member) is not str for member in members)
        ):
            raise MultiWindowIndependentTicketConsumerContractError(
                "source cluster partition is invalid"
            )
        result.append((cluster_id, tuple(members)))
    return tuple(result)


def _window_summary(
    binding: dict[str, Any],
    item: Any,
    *,
    strategy_id: str,
    variant_id: str,
    lane: str,
) -> tuple[dict[str, Any], tuple[Any, ...], tuple[str, ...]]:
    if type(item) is not dict or set(item) != _WINDOW_INPUT_KEYS:
        raise MultiWindowIndependentTicketConsumerContractError(
            "window input shape is invalid"
        )
    source = item["source_preregistration"]
    matrix = item["matrix"]
    cells = item["selection_cells"]
    gate = item["gate"]
    expected_source_hash = binding["source_preregistration_v2_hash"]
    if (
        type(source) is not dict
        or source.get("window_id") != binding["window_id"]
        or source.get("lookback_observations")
        != binding["lookback_observations"]
        or not _same_hash(
            source.get("preregistration_v2_hash"),
            expected_source_hash,
        )
    ):
        raise MultiWindowIndependentTicketConsumerContractError(
            "window source binding is invalid"
        )
    source_receipt = (
        source_v2.verify_correlation_cluster_window_source_preregistration_v2(
            source,
            expected_preregistration_v2_hash=expected_source_hash,
        )
    )
    matrix_receipt = source_v2.verify_correlation_cluster_window_matrix_v2(
        matrix,
        source,
        expected_preregistration_v2_hash=expected_source_hash,
    )
    gate_receipt = (
        source_v2.verify_correlation_cluster_window_independent_ticket_gate_v2(
            gate,
            source,
            matrix,
            cells,
            expected_preregistration_v2_hash=expected_source_hash,
            strategy_id=strategy_id,
            variant_id=variant_id,
            lane=lane,
        )
    )
    if (
        source_receipt.get("status") != "PASS"
        or matrix_receipt.get("status") != "PASS"
        or gate_receipt.get("status") != "PASS"
        or gate_receipt.get("gate_status") not in {"PASS", "BLOCK"}
        or type(gate_receipt.get("gate_status")) is not str
        or not _is_hash(matrix.get("matrix_v2_hash") if type(matrix) is dict else None)
        or not _is_hash(gate.get("gate_v2_hash") if type(gate) is dict else None)
    ):
        raise MultiWindowIndependentTicketConsumerContractError(
            "window exact verification failed"
        )
    symbols = source.get("symbols")
    if type(symbols) is not list or any(type(symbol) is not str for symbol in symbols):
        raise MultiWindowIndependentTicketConsumerContractError(
            "window symbol universe is invalid"
        )
    summary = {
        "window_id": binding["window_id"],
        "lookback_observations": binding["lookback_observations"],
        "source_preregistration_v2_hash": expected_source_hash,
        "matrix_v2_hash": matrix["matrix_v2_hash"],
        "gate_v2_hash": gate["gate_v2_hash"],
        "gate_status": gate_receipt["gate_status"],
        "gate_decision": gate_receipt["gate_decision"],
        "raw_passing_symbol_ticket_count": gate[
            "raw_passing_symbol_ticket_count"
        ],
        "effective_independent_ticket_count": gate[
            "effective_independent_ticket_count"
        ],
        "discounted_correlated_ticket_count": gate[
            "discounted_correlated_ticket_count"
        ],
    }
    for field in (
        "raw_passing_symbol_ticket_count",
        "effective_independent_ticket_count",
        "discounted_correlated_ticket_count",
    ):
        value = summary[field]
        if type(value) is not int or isinstance(value, bool) or value < 0:
            raise MultiWindowIndependentTicketConsumerContractError(
                "window ticket summary is invalid"
            )
    return summary, _partition_key(source), tuple(symbols)


def _seal_consumer(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "consumer_v3_hash")


def evaluate_multi_window_independent_ticket_consumer_v3(
    preregistration: Any,
    window_inputs: Any,
    *,
    expected_consumer_preregistration_v3_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": CONSUMER_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "UNKNOWN",
        "decision": "BLOCK_MULTI_WINDOW_SOURCE_UNVERIFIED",
        "strategy_id": strategy_id if type(strategy_id) is str else "",
        "variant_id": variant_id if type(variant_id) is str else "",
        "lane": lane if type(lane) is str else "",
        "consumer_preregistration_v3_hash": None,
        "first_blocking_tier": "SOURCE",
        "tiers": [],
        "blockers": [],
        "window_summaries": [],
        "summary": {
            "required_window_count": REQUIRED_WINDOW_COUNT,
            "verified_window_count": 0,
            "unique_matrix_hash_count": 0,
            "unique_partition_count": 0,
            "conservative_effective_independent_ticket_count": None,
            "maximum_raw_passing_symbol_ticket_count": None,
            "minimum_discounted_correlated_ticket_count": None,
        },
        "facts": {
            "all_windows_exactly_verified": False,
            "partition_stable": False,
            "all_window_gates_passed": False,
            "mock_verifier_used": False,
            "source_documents_embedded": False,
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
    except MultiWindowIndependentTicketConsumerContractError:
        clean_strategy_id = ""
        clean_variant_id = ""
        source_blockers.append("multi_window_identity_invalid")
    if type(lane) is not str or lane not in LANES:
        source_blockers.append("multi_window_lane_invalid")
    preregistration_receipt = (
        verify_multi_window_independent_ticket_consumer_preregistration_v3(
            preregistration,
            expected_consumer_preregistration_v3_hash=(
                expected_consumer_preregistration_v3_hash
            ),
        )
    )
    if preregistration_receipt["status"] != "PASS":
        source_blockers.append("multi_window_consumer_preregistration_invalid")
    bindings = (
        preregistration.get("window_bindings")
        if type(preregistration) is dict
        else None
    )
    expected_window_ids = (
        [binding["window_id"] for binding in bindings]
        if type(bindings) is list
        and all(type(binding) is dict and "window_id" in binding for binding in bindings)
        else []
    )
    if (
        type(window_inputs) is not dict
        or set(window_inputs) != set(expected_window_ids)
        or len(window_inputs) != REQUIRED_WINDOW_COUNT
    ):
        source_blockers.append("multi_window_input_coverage_invalid")

    summaries: list[dict[str, Any]] = []
    partitions: list[tuple[Any, ...]] = []
    universes: list[tuple[str, ...]] = []
    if not source_blockers:
        for binding in bindings:
            try:
                summary, partition, universe = _window_summary(
                    binding,
                    window_inputs[binding["window_id"]],
                    strategy_id=clean_strategy_id,
                    variant_id=clean_variant_id,
                    lane=lane,
                )
            except Exception:
                source_blockers.append(
                    f"window_source_unverified:{binding['window_id']}"
                )
                continue
            summaries.append(summary)
            partitions.append(partition)
            universes.append(universe)
    if (
        len({summary["matrix_v2_hash"] for summary in summaries})
        != len(summaries)
    ):
        source_blockers.append("multi_window_matrix_hashes_not_unique")
    if source_blockers:
        base["blockers"] = sorted(set(source_blockers))
        base["tiers"] = [
            {"tier_id": "SOURCE", "status": "BLOCK", "blockers": base["blockers"]},
            {"tier_id": "PARTITION_STABILITY", "status": "NOT_EVALUATED", "blockers": []},
            {"tier_id": "WINDOW_GATES", "status": "NOT_EVALUATED", "blockers": []},
        ]
        return _seal_consumer(base)

    base["consumer_preregistration_v3_hash"] = preregistration[
        "consumer_preregistration_v3_hash"
    ]
    base["facts"]["all_windows_exactly_verified"] = True
    partition_count = len(set(partitions))
    universe_count = len(set(universes))
    effective_counts = [
        summary["effective_independent_ticket_count"] for summary in summaries
    ]
    raw_counts = [summary["raw_passing_symbol_ticket_count"] for summary in summaries]
    discount_counts = [
        summary["discounted_correlated_ticket_count"] for summary in summaries
    ]
    base["window_summaries"] = summaries
    base["summary"] = {
        "required_window_count": REQUIRED_WINDOW_COUNT,
        "verified_window_count": len(summaries),
        "unique_matrix_hash_count": len(
            {summary["matrix_v2_hash"] for summary in summaries}
        ),
        "unique_partition_count": partition_count,
        "conservative_effective_independent_ticket_count": min(effective_counts),
        "maximum_raw_passing_symbol_ticket_count": max(raw_counts),
        "minimum_discounted_correlated_ticket_count": min(discount_counts),
    }
    if partition_count != 1 or universe_count != 1:
        base.update(
            {
                "status": "BLOCK",
                "decision": "BLOCK_MULTI_WINDOW_CLUSTER_PARTITION_DRIFT",
                "first_blocking_tier": "PARTITION_STABILITY",
                "blockers": ["multi_window_cluster_partition_not_stable"],
                "tiers": [
                    {"tier_id": "SOURCE", "status": "PASS", "blockers": []},
                    {"tier_id": "PARTITION_STABILITY", "status": "BLOCK", "blockers": ["multi_window_cluster_partition_not_stable"]},
                    {"tier_id": "WINDOW_GATES", "status": "NOT_EVALUATED", "blockers": []},
                ],
            }
        )
        return _seal_consumer(base)

    base["facts"]["partition_stable"] = True
    blocked_windows = [
        summary["window_id"]
        for summary in summaries
        if summary["gate_status"] != "PASS"
    ]
    if blocked_windows:
        blockers = [f"window_gate_blocked:{window_id}" for window_id in blocked_windows]
        base.update(
            {
                "status": "BLOCK",
                "decision": "BLOCK_MULTI_WINDOW_INDEPENDENT_TICKET_GATE",
                "first_blocking_tier": "WINDOW_GATES",
                "blockers": blockers,
                "tiers": [
                    {"tier_id": "SOURCE", "status": "PASS", "blockers": []},
                    {"tier_id": "PARTITION_STABILITY", "status": "PASS", "blockers": []},
                    {"tier_id": "WINDOW_GATES", "status": "BLOCK", "blockers": blockers},
                ],
            }
        )
        return _seal_consumer(base)

    base.update(
        {
            "status": "PASS",
            "decision": "PASS_MULTI_WINDOW_INDEPENDENT_TICKET_RESEARCH_CONSUMER",
            "first_blocking_tier": None,
            "blockers": [],
            "tiers": [
                {"tier_id": "SOURCE", "status": "PASS", "blockers": []},
                {"tier_id": "PARTITION_STABILITY", "status": "PASS", "blockers": []},
                {"tier_id": "WINDOW_GATES", "status": "PASS", "blockers": []},
            ],
        }
    )
    base["facts"]["all_window_gates_passed"] = True
    return _seal_consumer(base)


def verify_multi_window_independent_ticket_consumer_v3(
    document: Any,
    preregistration: Any,
    window_inputs: Any,
    *,
    expected_consumer_preregistration_v3_hash: Any,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_multi_window_independent_ticket_consumer_v3(
            preregistration,
            window_inputs,
            expected_consumer_preregistration_v3_hash=(
                expected_consumer_preregistration_v3_hash
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
        CONSUMER_VERIFICATION_SCHEMA_VERSION,
        [] if exact else ["multi_window_consumer_contract_invalid"],
        consumer_status=expected.get("status") if exact else "UNKNOWN",
        consumer_decision=expected.get("decision") if exact else "UNKNOWN",
        consumer_v3_hash=expected.get("consumer_v3_hash") if exact else None,
    )


__all__ = [
    "CONSUMER_SCHEMA_VERSION",
    "MultiWindowIndependentTicketConsumerContractError",
    "PREREGISTRATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_multi_window_independent_ticket_consumer_preregistration_v3",
    "evaluate_multi_window_independent_ticket_consumer_v3",
    "verify_multi_window_independent_ticket_consumer_preregistration_v3",
    "verify_multi_window_independent_ticket_consumer_v3",
]
