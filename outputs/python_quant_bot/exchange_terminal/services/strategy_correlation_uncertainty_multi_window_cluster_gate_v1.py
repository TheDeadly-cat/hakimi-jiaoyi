"""Unmounted conservative multi-window clustering over exact uncertainty audits.

The gate does not estimate correlations. It verifies the existing Fisher-Z
uncertainty audit for every preregistered window and treats a pair as separable
only when every window classifies that pair as CONFIRMED_LOW. Every other pair
becomes a dependence edge before deterministic connected components are built.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from hmac import compare_digest
from itertools import combinations
import json
from typing import Any

from exchange_terminal.services import strategy_correlation_uncertainty_audit as _uncertainty


SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-cluster-gate-contract-v1"
)
PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-cluster-preregistration-v1"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-cluster-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-uncertainty-multi-window-cluster-gate-v1-"
    "synthetic-unmounted-conservative-union-lock-1"
)
UNCERTAINTY_AUDIT_SOURCE_SHA256 = (
    "36c6139e2e92749ab70754a8c557aaf7a6ced52c6a1a182ee28fcccc1536e307"
)
MINIMUM_WINDOWS = 2
MAXIMUM_WINDOWS = 8
MAXIMUM_SYMBOLS = 64
PAIR_CLASSIFICATIONS = (
    "CONFIRMED_LOW",
    "CONFIRMED_HIGH",
    "AMBIGUOUS_THRESHOLD",
    "INSUFFICIENT_EFFECTIVE_SAMPLE",
)
PAIR_STATE_PRIORITY = (
    "INSUFFICIENT_EFFECTIVE_SAMPLE",
    "AMBIGUOUS_THRESHOLD",
    "CONFIRMED_HIGH",
    "CONFIRMED_LOW",
)
ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_PREREGISTRATION",
    "VERIFY_WINDOW_AUDITS_IN_PREREGISTERED_ORDER",
    "REQUIRE_EVERY_PAIR_IN_EVERY_WINDOW",
    "PROMOTE_EVERY_NON_CONFIRMED_LOW_PAIR_TO_DEPENDENCE_EDGE",
    "UNION_DEPENDENCE_EDGES_ACROSS_WINDOWS",
    "BUILD_TRANSITIVE_CONSERVATIVE_COMPONENTS",
    "COMPARE_COMPONENTS_WITH_PREREGISTERED_CLUSTERS",
    "CONSIDER_EFFECTIVE_BUDGET_CONSUMER_SEPARATELY",
)

_PAIR_FIELDS = frozenset(
    {
        "left_symbol",
        "right_symbol",
        "left_cluster_id",
        "right_cluster_id",
        "cross_cluster",
        "overlap_observations",
        "correlation",
        "absolute_correlation",
        "left_lag1_autocorrelation",
        "right_lag1_autocorrelation",
        "effective_observations",
        "absolute_correlation_interval_lower",
        "absolute_correlation_interval_upper",
        "classification",
    }
)
_WINDOW_INPUT_FIELDS = frozenset({"window_id", "uncertainty_audit"})
_BASE_BLOCKERS = (
    "UNMOUNTED_CANDIDATE",
    "NO_RUNTIME_CONSUMER_BOUND",
    "WINDOW_LABEL_ISSUER_BINDING_UNPROVEN",
    "NO_MARKET_RUNTIME_EVIDENCE",
    "PAPER_LIVE_UNAUTHORIZED",
)
_AUTHORITY = {
    "research_evidence_only": True,
    "current_admission_allowed": False,
    "effective_budget_activation_allowed": False,
    "http_registration_allowed": False,
    "runtime_activation_allowed": False,
    "writer_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return sha256(payload).hexdigest()


def _seal(document: dict[str, Any], field: str) -> dict[str, Any]:
    result = dict(document)
    result[field] = _canonical_hash(document)
    return result


def _exact_hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_symbols(value: Any) -> bool:
    return bool(
        type(value) is list
        and 2 <= len(value) <= MAXIMUM_SYMBOLS
        and all(
            type(symbol) is str
            and symbol
            and symbol == symbol.strip()
            for symbol in value
        )
        and value == sorted(value)
        and len(set(value)) == len(value)
    )


def _valid_windows(value: Any) -> bool:
    return bool(
        type(value) is list
        and MINIMUM_WINDOWS <= len(value) <= MAXIMUM_WINDOWS
        and all(
            type(window) is str
            and window
            and window == window.strip()
            for window in value
        )
        and len(set(value)) == len(value)
    )


def _cluster_membership(
    clusters: Any,
    symbols: list[str],
) -> dict[str, str] | None:
    if type(clusters) is not list or not clusters:
        return None
    membership: dict[str, str] = {}
    cluster_ids: list[str] = []
    for cluster in clusters:
        if type(cluster) is not dict or set(cluster) != {"cluster_id", "members"}:
            return None
        cluster_id = cluster.get("cluster_id")
        members = cluster.get("members")
        if (
            type(cluster_id) is not str
            or not cluster_id
            or cluster_id != cluster_id.strip()
            or type(members) is not list
            or not members
            or members != sorted(members)
            or len(set(members)) != len(members)
            or any(type(member) is not str or member not in symbols for member in members)
        ):
            return None
        cluster_ids.append(cluster_id)
        for member in members:
            if member in membership:
                return None
            membership[member] = cluster_id
    if (
        cluster_ids != sorted(cluster_ids)
        or len(set(cluster_ids)) != len(cluster_ids)
        or sorted(membership) != symbols
    ):
        return None
    return membership


_EXPECTED_POLICY = _uncertainty.build_strategy_correlation_uncertainty_policy()
EXPECTED_UNCERTAINTY_POLICY_HASH = _EXPECTED_POLICY["policy_hash"]
_CONTRACT_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "upstream_uncertainty_audit": {
        "module": (
            "exchange_terminal.services.strategy_correlation_uncertainty_audit"
        ),
        "source_sha256": UNCERTAINTY_AUDIT_SOURCE_SHA256,
        "audit_schema_version": (
            _uncertainty.STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION
        ),
        "policy_schema_version": (
            _uncertainty.STRATEGY_CORRELATION_UNCERTAINTY_POLICY_SCHEMA_VERSION
        ),
        "policy_hash": EXPECTED_UNCERTAINTY_POLICY_HASH,
        "verifier": "verify_strategy_correlation_uncertainty_audit",
    },
    "window_limits": {
        "minimum": MINIMUM_WINDOWS,
        "maximum": MAXIMUM_WINDOWS,
    },
    "maximum_symbols": MAXIMUM_SYMBOLS,
    "pair_classifications": list(PAIR_CLASSIFICATIONS),
    "separable_rule": "CONFIRMED_LOW_IN_EVERY_PREREGISTERED_WINDOW",
    "dependence_edge_rule": "ANY_NON_CONFIRMED_LOW_CLASSIFICATION",
    "window_aggregation": "CONSERVATIVE_EDGE_UNION",
    "component_method": "DETERMINISTIC_TRANSITIVE_CLOSURE",
    "activation_sequence": list(ACTIVATION_SEQUENCE),
}
GATE_CONTRACT_HASH = _canonical_hash(_CONTRACT_MANIFEST)


def build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
    expected_symbols: Any,
    expected_clusters: Any,
    expected_windows: Any,
) -> dict[str, Any] | None:
    if not _valid_symbols(expected_symbols) or not _valid_windows(expected_windows):
        return None
    membership = _cluster_membership(expected_clusters, expected_symbols)
    if membership is None:
        return None
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "upstream_uncertainty_audit_source_sha256": (
            UNCERTAINTY_AUDIT_SOURCE_SHA256
        ),
        "uncertainty_policy_hash": EXPECTED_UNCERTAINTY_POLICY_HASH,
        "expected_symbols": list(expected_symbols),
        "symbol_order_hash": _canonical_hash(expected_symbols),
        "expected_clusters": deepcopy(expected_clusters),
        "cluster_partition_hash": _canonical_hash(expected_clusters),
        "expected_windows": list(expected_windows),
        "window_order_hash": _canonical_hash(expected_windows),
        "parameters": {
            "minimum_windows": MINIMUM_WINDOWS,
            "maximum_windows": MAXIMUM_WINDOWS,
            "maximum_symbols": MAXIMUM_SYMBOLS,
            "separable_classification": "CONFIRMED_LOW",
            "separable_rule": "CONFIRMED_LOW_IN_EVERY_PREREGISTERED_WINDOW",
            "dependence_edge_rule": "ANY_NON_CONFIRMED_LOW_CLASSIFICATION",
            "window_aggregation": "CONSERVATIVE_EDGE_UNION",
            "component_method": "DETERMINISTIC_TRANSITIVE_CLOSURE",
        },
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "facts": {
            "thresholds_caller_overridable": False,
            "window_order_preregistered": True,
            "cluster_partition_preregistered": True,
            "all_windows_required": True,
            "synthetic_only": True,
            "mounted": False,
        },
        "blockers": list(_BASE_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(document, "preregistration_hash")


def verify_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
    document: Any,
    *,
    expected_symbols: Any,
    expected_clusters: Any,
    expected_windows: Any,
    expected_preregistration_hash: Any,
) -> bool:
    expected = (
        build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
            expected_symbols,
            expected_clusters,
            expected_windows,
        )
    )
    return bool(
        type(document) is dict
        and expected is not None
        and _exact_hash(expected_preregistration_hash)
        and document == expected
        and compare_digest(
            document["preregistration_hash"],
            expected_preregistration_hash,
        )
    )


def _window_audit(
    audit: Any,
    *,
    expected_audit_hash: str,
    symbols: list[str],
    clusters: list[dict[str, Any]],
    membership: dict[str, str],
) -> dict[tuple[str, str], dict[str, Any]] | None:
    if (
        type(audit) is not dict
        or audit.get("schema_version")
        != _uncertainty.STRATEGY_CORRELATION_UNCERTAINTY_AUDIT_SCHEMA_VERSION
        or audit.get("audit_hash") != expected_audit_hash
        or audit.get("policy_hash") != EXPECTED_UNCERTAINTY_POLICY_HASH
        or audit.get("policy") != _EXPECTED_POLICY
    ):
        return None
    try:
        verification = _uncertainty.verify_strategy_correlation_uncertainty_audit(
            audit
        )
    except Exception:
        return None
    if (
        type(verification) is not dict
        or verification.get("status") != "PASS"
        or verification.get("audit_hash") != expected_audit_hash
    ):
        return None
    replay = audit.get("matrix_replay")
    replay_preregistration = (
        replay.get("preregistration") if type(replay) is dict else None
    )
    if (
        type(replay_preregistration) is not dict
        or replay_preregistration.get("symbols") != symbols
        or replay_preregistration.get("clusters") != clusters
    ):
        return None
    expected_pairs = list(combinations(symbols, 2))
    pairs = audit.get("pairs")
    if (
        type(pairs) is not list
        or len(pairs) != len(expected_pairs)
        or audit.get("pair_count") != len(expected_pairs)
    ):
        return None
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for expected_pair, pair in zip(expected_pairs, pairs, strict=True):
        if type(pair) is not dict or frozenset(pair) != _PAIR_FIELDS:
            return None
        left, right = expected_pair
        classification = pair.get("classification")
        if (
            pair.get("left_symbol") != left
            or pair.get("right_symbol") != right
            or classification not in PAIR_CLASSIFICATIONS
            or pair.get("left_cluster_id") != membership[left]
            or pair.get("right_cluster_id") != membership[right]
            or pair.get("cross_cluster")
            is not (membership[left] != membership[right])
        ):
            return None
        result[expected_pair] = pair
    return result


def _conservative_state(classifications: list[str]) -> str:
    if "INSUFFICIENT_EFFECTIVE_SAMPLE" in classifications:
        return "INSUFFICIENT_SAMPLE_DEPENDENCE_EDGE"
    if "AMBIGUOUS_THRESHOLD" in classifications:
        return "AMBIGUOUS_DEPENDENCE_EDGE"
    if "CONFIRMED_HIGH" in classifications:
        return "CONFIRMED_DEPENDENCE_EDGE"
    return "CONFIRMED_LOW_ALL_WINDOWS"


def _components(
    symbols: list[str],
    dependence_pairs: list[tuple[str, str]],
    membership: dict[str, str],
) -> list[dict[str, Any]]:
    parent = {symbol: symbol for symbol in symbols}

    def find(symbol: str) -> str:
        while parent[symbol] != symbol:
            parent[symbol] = parent[parent[symbol]]
            symbol = parent[symbol]
        return symbol

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            parent[right_root] = left_root
        else:
            parent[left_root] = right_root

    for left, right in dependence_pairs:
        union(left, right)
    grouped: dict[str, list[str]] = {}
    for symbol in symbols:
        grouped.setdefault(find(symbol), []).append(symbol)
    ordered = sorted((sorted(members) for members in grouped.values()), key=tuple)
    return [
        {
            "component_id": f"component-{index:03d}",
            "members": members,
            "preregistered_cluster_ids": sorted(
                {membership[member] for member in members}
            ),
            "crosses_preregistered_clusters": (
                len({membership[member] for member in members}) > 1
            ),
        }
        for index, members in enumerate(ordered, start=1)
    ]


def _result(
    preregistration: dict[str, Any],
    *,
    status: str,
    reason_code: str,
    window_receipts: list[dict[str, Any]] | None = None,
    pair_assessments: list[dict[str, Any]] | None = None,
    components: list[dict[str, Any]] | None = None,
    cross_cluster_edges: list[dict[str, Any]] | None = None,
    gate_blockers: list[str] | None = None,
    all_windows_verified: bool = False,
) -> dict[str, Any]:
    receipts = window_receipts or []
    assessments = pair_assessments or []
    component_documents = components or []
    cross_edges = cross_cluster_edges or []
    blockers = gate_blockers or []
    document = {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "reason_code": reason_code,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "preregistration_hash": preregistration["preregistration_hash"],
        "uncertainty_policy_hash": EXPECTED_UNCERTAINTY_POLICY_HASH,
        "symbol_order_hash": preregistration["symbol_order_hash"],
        "cluster_partition_hash": preregistration["cluster_partition_hash"],
        "window_order_hash": preregistration["window_order_hash"],
        "window_receipts": deepcopy(receipts),
        "window_binding_hash": _canonical_hash(receipts) if receipts else None,
        "pair_assessments": deepcopy(assessments),
        "pair_assessment_hash": (
            _canonical_hash(assessments) if assessments else None
        ),
        "derived_conservative_components": deepcopy(component_documents),
        "derived_component_hash": (
            _canonical_hash(component_documents) if component_documents else None
        ),
        "cross_cluster_dependence_edges": deepcopy(cross_edges),
        "window_count": len(receipts),
        "pair_count": len(assessments),
        "dependence_edge_count": sum(
            item.get("dependence_edge") is True for item in assessments
        ),
        "cross_cluster_dependence_edge_count": len(cross_edges),
        "derived_conservative_component_count": len(component_documents),
        "preregistered_cluster_count": len(
            preregistration["expected_clusters"]
        ),
        "facts": {
            "all_windows_exactly_verified": all_windows_verified,
            "all_pairs_covered_in_every_window": all_windows_verified,
            "confirmed_low_required_in_every_window": True,
            "non_low_edges_unioned_across_windows": all_windows_verified,
            "transitive_dependence_components_derived": all_windows_verified,
            "cross_cluster_dependence_present": bool(cross_edges),
            "window_labels_issuer_bound": False,
            "raw_uncertainty_audits_embedded": False,
            "raw_price_or_return_series_embedded": False,
            "independence_units_claimed": False,
            "market_runtime_evidence_used": False,
            "synthetic_only": True,
            "mounted": False,
            "current_activated": False,
            "runtime_mutations_performed": False,
        },
        "gate_blockers": list(blockers),
        "activation_blockers": list(_BASE_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
    }
    return _seal(document, "gate_hash")


def evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
    preregistration: Any,
    window_audits: Any,
    *,
    expected_preregistration_hash: Any,
    expected_window_audit_hashes: Any,
) -> dict[str, Any] | None:
    if type(preregistration) is not dict:
        return None
    symbols = preregistration.get("expected_symbols")
    clusters = preregistration.get("expected_clusters")
    windows = preregistration.get("expected_windows")
    if not verify_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
        preregistration,
        expected_symbols=symbols,
        expected_clusters=clusters,
        expected_windows=windows,
        expected_preregistration_hash=expected_preregistration_hash,
    ):
        return None
    membership = _cluster_membership(clusters, symbols)
    if membership is None:
        return None
    if (
        type(window_audits) is not list
        or len(window_audits) != len(windows)
        or type(expected_window_audit_hashes) is not list
        or len(expected_window_audit_hashes) != len(windows)
        or any(not _exact_hash(value) for value in expected_window_audit_hashes)
        or len(set(expected_window_audit_hashes))
        != len(expected_window_audit_hashes)
    ):
        return _result(
            preregistration,
            status="UNKNOWN",
            reason_code="WINDOW_AUDIT_SET_NOT_EXACT",
            gate_blockers=["WINDOW_AUDIT_SET_NOT_EXACT"],
        )

    pair_maps: list[dict[tuple[str, str], dict[str, Any]]] = []
    receipts: list[dict[str, Any]] = []
    for index, expected_window in enumerate(windows):
        item = window_audits[index]
        expected_hash = expected_window_audit_hashes[index]
        if (
            type(item) is not dict
            or frozenset(item) != _WINDOW_INPUT_FIELDS
            or item.get("window_id") != expected_window
        ):
            return _result(
                preregistration,
                status="UNKNOWN",
                reason_code="WINDOW_ORDER_OR_SHAPE_NOT_EXACT",
                gate_blockers=["WINDOW_ORDER_OR_SHAPE_NOT_EXACT"],
            )
        try:
            pairs = _window_audit(
                item.get("uncertainty_audit"),
                expected_audit_hash=expected_hash,
                symbols=symbols,
                clusters=clusters,
                membership=membership,
            )
        except Exception:
            pairs = None
        if pairs is None:
            return _result(
                preregistration,
                status="UNKNOWN",
                reason_code="WINDOW_AUDIT_VERIFICATION_FAILED",
                gate_blockers=["WINDOW_AUDIT_VERIFICATION_FAILED"],
            )
        audit = item["uncertainty_audit"]
        pair_maps.append(pairs)
        receipts.append(
            {
                "window_id": expected_window,
                "audit_hash": expected_hash,
                "audit_status": audit["status"],
            }
        )

    assessments: list[dict[str, Any]] = []
    dependence_pairs: list[tuple[str, str]] = []
    cross_edges: list[dict[str, Any]] = []
    for left, right in combinations(symbols, 2):
        classifications = [
            pair_map[(left, right)]["classification"] for pair_map in pair_maps
        ]
        state = _conservative_state(classifications)
        dependence_edge = state != "CONFIRMED_LOW_ALL_WINDOWS"
        if dependence_edge:
            dependence_pairs.append((left, right))
        cross_cluster = membership[left] != membership[right]
        assessment = {
            "left_symbol": left,
            "right_symbol": right,
            "left_preregistered_cluster_id": membership[left],
            "right_preregistered_cluster_id": membership[right],
            "cross_preregistered_cluster": cross_cluster,
            "window_classifications": [
                {
                    "window_id": windows[index],
                    "classification": classification,
                }
                for index, classification in enumerate(classifications)
            ],
            "conservative_state": state,
            "dependence_edge": dependence_edge,
            "confirmed_high_window_count": classifications.count(
                "CONFIRMED_HIGH"
            ),
            "ambiguous_window_count": classifications.count(
                "AMBIGUOUS_THRESHOLD"
            ),
            "insufficient_sample_window_count": classifications.count(
                "INSUFFICIENT_EFFECTIVE_SAMPLE"
            ),
        }
        assessments.append(assessment)
        if dependence_edge and cross_cluster:
            cross_edges.append(
                {
                    "left_symbol": left,
                    "right_symbol": right,
                    "conservative_state": state,
                }
            )

    component_documents = _components(symbols, dependence_pairs, membership)
    if cross_edges:
        return _result(
            preregistration,
            status="BLOCK",
            reason_code=(
                "CROSS_CLUSTER_DEPENDENCE_NOT_CONSERVATIVELY_GROUPED"
            ),
            window_receipts=receipts,
            pair_assessments=assessments,
            components=component_documents,
            cross_cluster_edges=cross_edges,
            gate_blockers=["CROSS_CLUSTER_DEPENDENCE_EDGE_PRESENT"],
            all_windows_verified=True,
        )
    return _result(
        preregistration,
        status="PASS",
        reason_code="ALL_DEPENDENCE_EDGES_WITHIN_PREREGISTERED_CLUSTERS",
        window_receipts=receipts,
        pair_assessments=assessments,
        components=component_documents,
        cross_cluster_edges=[],
        gate_blockers=[],
        all_windows_verified=True,
    )


def verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
    document: Any,
    preregistration: Any,
    window_audits: Any,
    *,
    expected_gate_hash: Any,
    expected_preregistration_hash: Any,
    expected_window_audit_hashes: Any,
) -> bool:
    if type(document) is not dict or not _exact_hash(expected_gate_hash):
        return False
    expected = evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
        preregistration,
        window_audits,
        expected_preregistration_hash=expected_preregistration_hash,
        expected_window_audit_hashes=expected_window_audit_hashes,
    )
    return bool(
        type(expected) is dict
        and document == expected
        and document.get("gate_hash") == expected_gate_hash
        and compare_digest(expected["gate_hash"], expected_gate_hash)
    )


__all__ = [
    "ACTIVATION_SEQUENCE",
    "EXPECTED_UNCERTAINTY_POLICY_HASH",
    "GATE_CONTRACT_HASH",
    "GATE_SCHEMA_VERSION",
    "MAXIMUM_SYMBOLS",
    "MAXIMUM_WINDOWS",
    "MINIMUM_WINDOWS",
    "PAIR_CLASSIFICATIONS",
    "PREREGISTRATION_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNCERTAINTY_AUDIT_SOURCE_SHA256",
    "build_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1",
    "evaluate_strategy_correlation_uncertainty_multi_window_cluster_gate_v1",
    "verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1",
    "verify_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1",
]
