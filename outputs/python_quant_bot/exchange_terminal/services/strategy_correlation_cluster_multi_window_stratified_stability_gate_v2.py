"""Pre-registered multi-window stability gate for stratified budget-v3.

Risk-increasing proposals must exactly verify one budget-v3 document for every
registered lookback. Any window block, complete-link partition drift, or strata
topology drift blocks the local research gate. Risk reduction remains source
free. This module has no runtime, current, paper, live, or order authority.
"""

from __future__ import annotations

import copy
import hmac
import math
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-stratified-stability-"
    "preregistration-v2"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-stratified-stability-gate-v2"
)
VERIFICATION_SCHEMA_VERSION = f"{GATE_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-multi-window-stratified-stability-gate-v2-lock-1"
)
BUDGET_V3_IMPLEMENTATION_SHA256 = (
    "bece44fe40c02242c879d1dead5cc11d2ce00edfc91c8d78a5b29962516c002d"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
REQUIRED_WINDOW_COUNT = 3
WINDOW_AGGREGATION_POLICY = "ANY_EXACT_WINDOW_V3_BLOCKS_RISK_INCREASE"
PARTITION_STABILITY_POLICY = (
    "REQUIRE_IDENTICAL_COMPLETE_LINK_PARTITION_FOR_RISK_INCREASE"
)
STRATA_TOPOLOGY_STABILITY_POLICY = (
    "REQUIRE_IDENTICAL_PREREGISTERED_STRATA_TOPOLOGY_FOR_RISK_INCREASE"
)
RISK_REDUCTION_POLICY = "SOURCE_FREE_RISK_REDUCTION"
WINDOW_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration",
        "correlation_matrix",
        "complete_link_audit",
        "strata_registration",
        "strata_gate",
        "complete_link_gate",
        "equity",
        "positions",
        "proposed_symbol",
        "proposed_notional",
        "proposed_direction",
        "max_cluster_gross_pct",
        "risk_increasing",
    }
)

_VERIFY_BUDGET_V3 = (
    budget_v3.verify_strategy_correlation_cluster_effective_bet_budget_v3
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOW_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_BUDGET_KEYS = {
    "authority",
    "blockers",
    "budget_v3_hash",
    "checks",
    "decision",
    "facts",
    "policy",
    "portfolio",
    "schema_version",
    "source",
    "static_fingerprint",
    "status",
}
_PORTFOLIO_KEYS = {
    "active_cluster_count",
    "active_dimension_count",
    "conservative_weighted_effective_strata_count",
    "dimension_results",
    "symbol_ticket_count",
    "total_active_gross_pct",
    "v2_weighted_effective_cluster_count",
    "weighted_diversification_gate_applied",
}
_DIMENSION_KEYS = {
    "active_stratum_count",
    "dimension_id",
    "diversification_status",
    "dominant_stratum_id",
    "dominant_stratum_share_of_active_gross_pct",
    "gross_limit_status",
    "maximum_stratum_gross_pct",
    "over_limit_stratum_count",
    "status",
    "weighted_effective_strata_count",
}
_RECEIPT_KEYS = {
    "budget_decision",
    "budget_v3_hash",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "runtime_gate_activation_allowed",
    "schema_version",
    "status",
    "writer_allowed",
}


class MultiWindowStratifiedStabilityContractError(ValueError):
    """Raised when a preregistration cannot be made deterministic."""


def _exact_keys(value: Any, expected: set[str] | frozenset[str]) -> bool:
    return type(value) is dict and set(value) == set(expected)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _sealed_hash_exact(document: Any, field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(field)):
        return False
    try:
        rebuilt = seal_strict_canonical_document(document, field)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(document[field], rebuilt[field])


def _number_or_none(value: Any) -> bool:
    if value is None:
        return True
    return (
        type(value) in {int, float}
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    return (
        type(authority) is dict
        and authority.get("descriptive_only") is True
        and authority.get("writer_allowed") is False
        and authority.get("runtime_gate_activation_allowed") is False
        and authority.get("current_admission_allowed") is False
        and authority.get("paper_authorized") is False
        and authority.get("live_order_allowed") is False
    )


def _validate_window_specs(window_specs: Any) -> list[dict[str, Any]]:
    if type(window_specs) is not list or len(window_specs) != REQUIRED_WINDOW_COUNT:
        raise MultiWindowStratifiedStabilityContractError(
            "exactly three windows are required"
        )
    normalized: list[dict[str, Any]] = []
    window_ids: set[str] = set()
    previous_lookback = 0
    for item in window_specs:
        if not _exact_keys(item, {"window_id", "lookback_observations"}):
            raise MultiWindowStratifiedStabilityContractError(
                "window spec shape is invalid"
            )
        window_id = item["window_id"]
        lookback = item["lookback_observations"]
        if type(window_id) is not str or _WINDOW_ID_RE.fullmatch(window_id) is None:
            raise MultiWindowStratifiedStabilityContractError("window_id is invalid")
        if window_id in window_ids:
            raise MultiWindowStratifiedStabilityContractError(
                "window_id must be unique"
            )
        if (
            type(lookback) is not int
            or isinstance(lookback, bool)
            or lookback < 20
            or lookback <= previous_lookback
        ):
            raise MultiWindowStratifiedStabilityContractError(
                "lookbacks must be integers >= 20 in strictly increasing order"
            )
        window_ids.add(window_id)
        previous_lookback = lookback
        normalized.append(
            {"window_id": window_id, "lookback_observations": lookback}
        )
    return normalized


def build_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2(
    window_specs: Any,
) -> dict[str, Any]:
    """Freeze windows and all conservative aggregation policies before data."""
    specs = _validate_window_specs(window_specs)
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "facts": {
                "profitability_proven": False,
                "runtime_assets_accessed": False,
                "window_data_observed_by_builder": False,
                "windows_selected_before_evaluation": True,
            },
            "implementation_pins": {
                "budget_v3": BUDGET_V3_IMPLEMENTATION_SHA256,
                "strict_canonical_json_hash": (
                    STRICT_CANONICAL_IMPLEMENTATION_SHA256
                ),
            },
            "partition_stability_policy": PARTITION_STABILITY_POLICY,
            "required_window_count": REQUIRED_WINDOW_COUNT,
            "risk_reduction_policy": RISK_REDUCTION_POLICY,
            "schema_version": PREREGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "PREREGISTERED_RESEARCH_ONLY",
            "strata_topology_stability_policy": (
                STRATA_TOPOLOGY_STABILITY_POLICY
            ),
            "window_aggregation_policy": WINDOW_AGGREGATION_POLICY,
            "window_specs": specs,
        },
        "preregistration_v2_hash",
    )


def verify_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2(
    document: Any,
    window_specs: Any,
    *,
    expected_preregistration_v2_hash: Any,
) -> bool:
    if not _same_hash(
        document.get("preregistration_v2_hash") if type(document) is dict else None,
        expected_preregistration_v2_hash,
    ):
        return False
    try:
        expected = build_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2(
            window_specs
        )
    except (MultiWindowStratifiedStabilityContractError, TypeError, ValueError):
        return False
    return type(document) is dict and strict_json_contract_equal(document, expected)


def _preregistration_presentable(document: Any, expected_hash: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != PREREGISTRATION_SCHEMA_VERSION
        or document.get("static_fingerprint") != STATIC_FINGERPRINT
        or document.get("status") != "PREREGISTERED_RESEARCH_ONLY"
        or document.get("required_window_count") != REQUIRED_WINDOW_COUNT
        or document.get("window_aggregation_policy") != WINDOW_AGGREGATION_POLICY
        or document.get("partition_stability_policy")
        != PARTITION_STABILITY_POLICY
        or document.get("strata_topology_stability_policy")
        != STRATA_TOPOLOGY_STABILITY_POLICY
        or document.get("risk_reduction_policy") != RISK_REDUCTION_POLICY
        or not _same_hash(document.get("preregistration_v2_hash"), expected_hash)
        or not _sealed_hash_exact(document, "preregistration_v2_hash")
        or not _authority_locked(document)
    ):
        return False
    try:
        specs = _validate_window_specs(document.get("window_specs"))
    except MultiWindowStratifiedStabilityContractError:
        return False
    return (
        specs == document["window_specs"]
        and document.get("implementation_pins")
        == {
            "budget_v3": BUDGET_V3_IMPLEMENTATION_SHA256,
            "strict_canonical_json_hash": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        }
        and document.get("facts")
        == {
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "window_data_observed_by_builder": False,
            "windows_selected_before_evaluation": True,
        }
    )


def _context_valid(context: Any) -> bool:
    if not _exact_keys(context, WINDOW_VERIFICATION_CONTEXT_KEYS):
        return False
    dict_fields = {
        "preregistration",
        "correlation_matrix",
        "complete_link_audit",
        "strata_registration",
        "strata_gate",
        "complete_link_gate",
    }
    return (
        all(type(context[field]) is dict for field in dict_fields)
        and type(context["positions"]) is list
        and type(context["proposed_symbol"]) is str
        and type(context["proposed_direction"]) is str
        and type(context["risk_increasing"]) is bool
    )


def _receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(receipt, _RECEIPT_KEYS)
        and receipt["schema_version"] == budget_v3.BUDGET_VERIFICATION_SCHEMA_VERSION
        and receipt["status"] == "PASS"
        and receipt["budget_decision"] == document.get("decision")
        and receipt["budget_v3_hash"] == document.get("budget_v3_hash")
        and receipt["runtime_gate_activation_allowed"] is False
        and receipt["current_admission_allowed"] is False
        and receipt["writer_allowed"] is False
        and receipt["paper_authorized"] is False
        and receipt["live_order_allowed"] is False
    )


def _call_budget_v3_verifier(document: Any, context: Any) -> bool:
    if not _context_valid(context):
        return False
    try:
        receipt = _VERIFY_BUDGET_V3(
            copy.deepcopy(document),
            copy.deepcopy(context["preregistration"]),
            copy.deepcopy(context["correlation_matrix"]),
            copy.deepcopy(context["complete_link_audit"]),
            strata_registration=copy.deepcopy(context["strata_registration"]),
            strata_gate=copy.deepcopy(context["strata_gate"]),
            complete_link_gate=copy.deepcopy(context["complete_link_gate"]),
            equity=copy.deepcopy(context["equity"]),
            positions=copy.deepcopy(context["positions"]),
            proposed_symbol=context["proposed_symbol"],
            proposed_notional=copy.deepcopy(context["proposed_notional"]),
            proposed_direction=context["proposed_direction"],
            max_cluster_gross_pct=copy.deepcopy(
                context["max_cluster_gross_pct"]
            ),
            risk_increasing=context["risk_increasing"],
        )
    except Exception:
        return False
    return _receipt_valid(receipt, document)


def _dimension_row_valid(row: Any) -> bool:
    return (
        _exact_keys(row, _DIMENSION_KEYS)
        and type(row["dimension_id"]) is str
        and bool(row["dimension_id"])
        and type(row["dominant_stratum_id"]) is str
        and bool(row["dominant_stratum_id"])
        and type(row["active_stratum_count"]) is int
        and not isinstance(row["active_stratum_count"], bool)
        and row["active_stratum_count"] >= 0
        and type(row["over_limit_stratum_count"]) is int
        and not isinstance(row["over_limit_stratum_count"], bool)
        and row["over_limit_stratum_count"] >= 0
        and row["diversification_status"] in {"PASS", "BLOCK", "NOT_APPLICABLE"}
        and row["gross_limit_status"] in {"PASS", "BLOCK"}
        and row["status"] in {"PASS", "BLOCK"}
        and _number_or_none(row["dominant_stratum_share_of_active_gross_pct"])
        and _number_or_none(row["maximum_stratum_gross_pct"])
        and _number_or_none(row["weighted_effective_strata_count"])
    )


def _registration_dimension_ids(registration: Any) -> list[str] | None:
    topology = _strata_topology(registration)
    return [item["dimension_id"] for item in topology] if topology is not None else None


def _budget_document_presentable(document: Any, context: Any) -> bool:
    if (
        not _exact_keys(document, _BUDGET_KEYS)
        or document.get("schema_version") != budget_v3.BUDGET_SCHEMA_VERSION
        or document.get("static_fingerprint") != budget_v3.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or type(document.get("decision")) is not str
        or not document["decision"]
        or not _sealed_hash_exact(document, "budget_v3_hash")
        or not _authority_locked(document)
    ):
        return False
    source = document["source"]
    portfolio = document["portfolio"]
    blockers = document["blockers"]
    rows = portfolio.get("dimension_results") if type(portfolio) is dict else None
    dimension_ids = _registration_dimension_ids(context["strata_registration"])
    if (
        type(source) is not dict
        or not _exact_keys(portfolio, _PORTFOLIO_KEYS)
        or type(blockers) is not list
        or any(type(item) is not str for item in blockers)
        or type(rows) is not list
        or not rows
        or any(not _dimension_row_valid(row) for row in rows)
        or dimension_ids is None
        or sorted(row["dimension_id"] for row in rows) != dimension_ids
        or portfolio["active_dimension_count"] != len(rows)
        or not _number_or_none(
            portfolio["conservative_weighted_effective_strata_count"]
        )
        or not _number_or_none(portfolio["total_active_gross_pct"])
        or not _number_or_none(portfolio["v2_weighted_effective_cluster_count"])
        or type(portfolio["weighted_diversification_gate_applied"]) is not bool
        or not _same_hash(
            source.get("strata_registration_hash"),
            context["strata_registration"].get("registration_hash"),
        )
        or not _same_hash(
            source.get("strata_gate_hash"), context["strata_gate"].get("gate_hash")
        )
        or not _same_hash(
            source.get("complete_link_gate_hash"),
            context["complete_link_gate"].get("gate_hash"),
        )
        or document.get("facts", {}).get("risk_increasing")
        is not context["risk_increasing"]
    ):
        return False
    return (document["status"] == "PASS" and blockers == []) or (
        document["status"] == "BLOCK" and bool(blockers)
    )


def _matrix_and_partition(
    context: dict[str, Any], expected_lookback: int
) -> tuple[str, tuple[tuple[str, ...], ...]] | None:
    matrix = context["correlation_matrix"]
    audit = context["complete_link_audit"]
    matrix_permissions = matrix.get("permissions")
    audit_permissions = audit.get("permissions")
    if (
        matrix.get("schema_version") != "strategy-selection-correlation-matrix-v1"
        or matrix.get("status") != "PASS"
        or matrix.get("lookback_observations") != expected_lookback
        or not _is_hash(matrix.get("matrix_hash"))
        or type(matrix.get("symbols")) is not list
        or any(type(symbol) is not str or not symbol for symbol in matrix["symbols"])
        or matrix.get("return_series") != "COMPLETED_DAILY_RETURNS"
        or type(matrix_permissions) is not dict
        or matrix_permissions.get("paper_authorized") is not False
        or matrix_permissions.get("live_order_allowed") is not False
        or audit.get("schema_version")
        != "strategy-correlation-cluster-complete-link-audit-v1"
        or audit.get("status") != "PASS"
        or not _same_hash(audit.get("matrix_hash"), matrix["matrix_hash"])
        or type(audit_permissions) is not dict
        or audit_permissions.get("paper_authorized") is not False
        or audit_permissions.get("live_order_allowed") is not False
        or type(audit.get("cluster_results")) is not list
    ):
        return None
    clusters: list[tuple[str, ...]] = []
    cluster_ids: set[str] = set()
    for item in audit["cluster_results"]:
        cluster_id = item.get("cluster_id") if type(item) is dict else None
        members = item.get("members") if type(item) is dict else None
        if (
            type(cluster_id) is not str
            or not cluster_id
            or cluster_id in cluster_ids
            or type(members) is not list
            or not members
            or any(type(member) is not str or not member for member in members)
            or len(set(members)) != len(members)
        ):
            return None
        cluster_ids.add(cluster_id)
        clusters.append(tuple(sorted(members)))
    partition = tuple(sorted(clusters))
    flattened = [member for cluster in partition for member in cluster]
    if sorted(flattened) != sorted(matrix["symbols"]) or len(flattened) != len(
        set(flattened)
    ):
        return None
    return matrix["matrix_hash"], partition


def _strata_topology(registration: Any) -> list[dict[str, Any]] | None:
    dimensions = registration.get("dimensions") if type(registration) is dict else None
    if type(dimensions) is not list or not dimensions:
        return None
    normalized: list[dict[str, Any]] = []
    dimension_ids: set[str] = set()
    for dimension in dimensions:
        if not _exact_keys(dimension, {"dimension_id", "strata"}):
            return None
        dimension_id = dimension["dimension_id"]
        strata = dimension["strata"]
        if (
            type(dimension_id) is not str
            or not dimension_id
            or dimension_id in dimension_ids
            or type(strata) is not list
            or not strata
        ):
            return None
        dimension_ids.add(dimension_id)
        normalized_strata: list[dict[str, Any]] = []
        stratum_ids: set[str] = set()
        seen_clusters: set[str] = set()
        for stratum in strata:
            if not _exact_keys(stratum, {"cluster_ids", "stratum_id"}):
                return None
            stratum_id = stratum["stratum_id"]
            cluster_ids = stratum["cluster_ids"]
            if (
                type(stratum_id) is not str
                or not stratum_id
                or stratum_id in stratum_ids
                or type(cluster_ids) is not list
                or not cluster_ids
                or any(type(value) is not str or not value for value in cluster_ids)
                or len(set(cluster_ids)) != len(cluster_ids)
                or seen_clusters.intersection(cluster_ids)
            ):
                return None
            stratum_ids.add(stratum_id)
            seen_clusters.update(cluster_ids)
            normalized_strata.append(
                {"cluster_ids": sorted(cluster_ids), "stratum_id": stratum_id}
            )
        normalized.append(
            {
                "dimension_id": dimension_id,
                "strata": sorted(
                    normalized_strata, key=lambda item: item["stratum_id"]
                ),
            }
        )
    return sorted(normalized, key=lambda item: item["dimension_id"])


def _identity_payload(context: dict[str, Any]) -> dict[str, Any]:
    matrix = context["correlation_matrix"]
    source_preregistration = context["preregistration"]
    audit = context["complete_link_audit"]
    return {
        "absolute_pearson_threshold": audit.get("absolute_pearson_threshold"),
        "equity": copy.deepcopy(context["equity"]),
        "matrix_symbols": copy.deepcopy(matrix.get("symbols")),
        "max_cluster_gross_pct": copy.deepcopy(context["max_cluster_gross_pct"]),
        "positions": copy.deepcopy(context["positions"]),
        "preregistration_symbols": copy.deepcopy(
            source_preregistration.get("symbols")
        ),
        "proposed_direction": context["proposed_direction"],
        "proposed_notional": copy.deepcopy(context["proposed_notional"]),
        "proposed_symbol": context["proposed_symbol"],
        "return_series": matrix.get("return_series"),
        "risk_increasing": context["risk_increasing"],
    }


def _source_summary(
    specs: list[dict[str, Any]],
    documents: Any,
    contexts: Any,
) -> dict[str, Any] | None:
    window_ids = [item["window_id"] for item in specs]
    if (
        type(documents) is not dict
        or type(contexts) is not dict
        or set(documents) != set(window_ids)
        or set(contexts) != set(window_ids)
    ):
        return None
    summaries: list[dict[str, Any]] = []
    matrix_hashes: set[str] = set()
    partition_hashes: list[str] = []
    topology_hashes: list[str] = []
    identity_hash: str | None = None
    for spec in specs:
        window_id = spec["window_id"]
        document = documents[window_id]
        context = contexts[window_id]
        if (
            not _context_valid(context)
            or context["risk_increasing"] is not True
            or not _call_budget_v3_verifier(document, context)
            or not _budget_document_presentable(document, context)
        ):
            return None
        matrix_partition = _matrix_and_partition(
            context, spec["lookback_observations"]
        )
        topology = _strata_topology(context["strata_registration"])
        if matrix_partition is None or topology is None:
            return None
        matrix_hash, partition = matrix_partition
        if matrix_hash in matrix_hashes:
            return None
        matrix_hashes.add(matrix_hash)
        try:
            current_identity_hash = strict_canonical_hash(_identity_payload(context))
        except (TypeError, ValueError):
            return None
        if identity_hash is None:
            identity_hash = current_identity_hash
        elif not hmac.compare_digest(identity_hash, current_identity_hash):
            return None
        partition_hash = strict_canonical_hash(
            {"complete_link_partition": [list(cluster) for cluster in partition]}
        )
        topology_hash = strict_canonical_hash({"strata_topology": topology})
        partition_hashes.append(partition_hash)
        topology_hashes.append(topology_hash)
        portfolio = document["portfolio"]
        rows = portfolio["dimension_results"]
        maximum_values = [
            row["maximum_stratum_gross_pct"]
            for row in rows
            if row["maximum_stratum_gross_pct"] is not None
        ]
        summaries.append(
            {
                "active_dimension_count": portfolio["active_dimension_count"],
                "blocked_dimension_count": sum(
                    row["status"] == "BLOCK" for row in rows
                ),
                "budget_decision": document["decision"],
                "budget_status": document["status"],
                "budget_v3_exactly_verified": True,
                "budget_v3_hash": document["budget_v3_hash"],
                "cluster_partition_hash": partition_hash,
                "conservative_weighted_effective_strata_count": portfolio[
                    "conservative_weighted_effective_strata_count"
                ],
                "lookback_observations": spec["lookback_observations"],
                "matrix_hash": matrix_hash,
                "maximum_active_stratum_gross_pct": (
                    max(maximum_values) if maximum_values else None
                ),
                "strata_topology_hash": topology_hash,
                "window_id": window_id,
            }
        )
    return {
        "identity_hash": identity_hash,
        "matrix_hashes": matrix_hashes,
        "partition_stable": len(set(partition_hashes)) == 1,
        "summaries": summaries,
        "topology_stable": len(set(topology_hashes)) == 1,
    }


def evaluate_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2(
    preregistration: Any,
    window_budget_v3_documents: Any,
    *,
    window_verification_contexts: Any,
    expected_preregistration_v2_hash: Any,
    risk_increasing: Any,
) -> dict[str, Any]:
    """Evaluate exact registered windows without embedding source documents."""
    risk_flag = risk_increasing if type(risk_increasing) is bool else None
    preregistration_exact = False
    specs: list[dict[str, Any]] = []
    source_result: dict[str, Any] | None = None
    if risk_flag is True:
        preregistration_exact = _preregistration_presentable(
            preregistration, expected_preregistration_v2_hash
        )
        if preregistration_exact:
            specs = copy.deepcopy(preregistration["window_specs"])
            source_result = _source_summary(
                specs, window_budget_v3_documents, window_verification_contexts
            )
    known = risk_flag is True and preregistration_exact and source_result is not None
    summaries = source_result["summaries"] if known else []
    partition_stable = source_result["partition_stable"] if known else False
    topology_stable = source_result["topology_stable"] if known else False
    identity_hash = source_result["identity_hash"] if known else None
    any_blocked = known and any(item["budget_status"] == "BLOCK" for item in summaries)

    if risk_flag is False:
        status = "PASS"
        decision = "PASS_RISK_REDUCTION_SOURCE_FREE"
        blockers: list[str] = []
    elif not known or not _is_hash(identity_hash):
        status = "UNKNOWN"
        decision = "BLOCK_MULTI_WINDOW_STRATIFIED_SOURCE_UNVERIFIED"
        blockers = ["multi_window_stratified_source_verification"]
    elif any_blocked:
        status = "BLOCK"
        decision = "BLOCK_REGISTERED_WINDOW_STRATIFIED_BUDGET"
        blockers = ["registered_window_stratified_budget_block"]
    elif not partition_stable:
        status = "BLOCK"
        decision = "BLOCK_REGISTERED_WINDOW_CLUSTER_PARTITION_DRIFT"
        blockers = ["registered_window_cluster_partition_drift"]
    elif not topology_stable:
        status = "BLOCK"
        decision = "BLOCK_REGISTERED_WINDOW_STRATA_TOPOLOGY_DRIFT"
        blockers = ["registered_window_strata_topology_drift"]
    else:
        status = "PASS"
        decision = "PASS_MULTI_WINDOW_STRATIFIED_STABLE_RESEARCH_GATE"
        blockers = []

    effective_counts = [
        item["conservative_weighted_effective_strata_count"]
        for item in summaries
        if item["conservative_weighted_effective_strata_count"] is not None
    ]
    maximum_gross_values = [
        item["maximum_active_stratum_gross_pct"]
        for item in summaries
        if item["maximum_active_stratum_gross_pct"] is not None
    ]
    decision_pairs = {
        (item["budget_status"], item["budget_decision"]) for item in summaries
    }
    document = {
        "authority": _authority(),
        "blockers": blockers,
        "decision": decision,
        "facts": {
            "all_registered_windows_exactly_verified": known,
            "any_registered_window_blocked": any_blocked,
            "cluster_partition_stable": partition_stable,
            "correlation_matrices_embedded": False,
            "matrix_hashes_unique_across_windows": known,
            "positions_embedded": False,
            "preregistration_exactly_verified": preregistration_exact,
            "profitability_proven": False,
            "risk_reduction_source_free": risk_flag is False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "single_window_independence_assumption_used": False,
            "source_documents_embedded": False,
            "strata_topology_stable": topology_stable,
            "trade_identity_consistent_across_windows": known,
            "verification_contexts_embedded": False,
        },
        "policy": {
            "partition_stability_policy": PARTITION_STABILITY_POLICY,
            "risk_reduction_policy": RISK_REDUCTION_POLICY,
            "strata_topology_stability_policy": (
                STRATA_TOPOLOGY_STABILITY_POLICY
            ),
            "window_aggregation_policy": WINDOW_AGGREGATION_POLICY,
        },
        "schema_version": GATE_SCHEMA_VERSION,
        "source": {
            "budget_v3_implementation_sha256": BUDGET_V3_IMPLEMENTATION_SHA256,
            "preregistration_v2_hash": (
                preregistration.get("preregistration_v2_hash")
                if preregistration_exact
                else None
            ),
            "source_documents_embedded": False,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "trade_identity_hash": identity_hash if known else None,
            "verification_contexts_embedded": False,
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "any_registered_window_blocked": any_blocked,
            "cluster_partition_stable": partition_stable,
            "minimum_conservative_weighted_effective_strata_count": (
                min(effective_counts) if effective_counts else None
            ),
            "registered_window_count": len(specs),
            "risk_increasing": risk_flag,
            "strata_topology_stable": topology_stable,
            "unique_matrix_hash_count": (
                len(source_result["matrix_hashes"]) if known else 0
            ),
            "unique_partition_count": (
                len({item["cluster_partition_hash"] for item in summaries})
            ),
            "unique_strata_topology_count": (
                len({item["strata_topology_hash"] for item in summaries})
            ),
            "verified_window_count": len(summaries),
            "window_budget_decision_variant_count": len(decision_pairs),
            "worst_window_maximum_active_stratum_gross_pct": (
                max(maximum_gross_values) if maximum_gross_values else None
            ),
        },
        "window_summaries": summaries,
    }
    return seal_strict_canonical_document(document, "stability_gate_v2_hash")


def verify_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2(
    document: Any,
    preregistration: Any,
    window_budget_v3_documents: Any,
    *,
    window_verification_contexts: Any,
    expected_preregistration_v2_hash: Any,
    risk_increasing: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2(
            preregistration,
            window_budget_v3_documents,
            window_verification_contexts=window_verification_contexts,
            expected_preregistration_v2_hash=expected_preregistration_v2_hash,
            risk_increasing=risk_increasing,
        )
        exact = (
            type(document) is dict
            and strict_json_contract_equal(document, expected)
            and document.get("schema_version") == GATE_SCHEMA_VERSION
            and document.get("status") in {"PASS", "BLOCK"}
            and _sealed_hash_exact(document, "stability_gate_v2_hash")
            and _authority_locked(document)
        )
    except Exception:
        exact = False
    return {
        "blockers": [] if exact else ["multi_window_stratified_stability_exact_rebuild"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "stability_gate_decision": (
            document.get("decision") if exact and type(document) is dict else "UNKNOWN"
        ),
        "stability_gate_exactly_verified": exact,
        "stability_gate_status": (
            document.get("status") if exact and type(document) is dict else "UNKNOWN"
        ),
        "stability_gate_v2_hash": (
            document.get("stability_gate_v2_hash")
            if exact and type(document) is dict
            else None
        ),
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


__all__ = [
    "BUDGET_V3_IMPLEMENTATION_SHA256",
    "GATE_SCHEMA_VERSION",
    "MultiWindowStratifiedStabilityContractError",
    "PARTITION_STABILITY_POLICY",
    "PREREGISTRATION_SCHEMA_VERSION",
    "REQUIRED_WINDOW_COUNT",
    "RISK_REDUCTION_POLICY",
    "STATIC_FINGERPRINT",
    "STRATA_TOPOLOGY_STABILITY_POLICY",
    "VERIFICATION_SCHEMA_VERSION",
    "WINDOW_AGGREGATION_POLICY",
    "WINDOW_VERIFICATION_CONTEXT_KEYS",
    "build_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2",
    "evaluate_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2",
    "verify_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2",
    "verify_strategy_correlation_cluster_multi_window_stratified_stability_preregistration_v2",
]
