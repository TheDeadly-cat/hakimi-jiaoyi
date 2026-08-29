"""Pre-registered multi-window stability gate for correlation clusters.

The gate re-verifies one weighted-budget-v2 document per registered lookback.
For risk-increasing proposals, any window budget block or any cluster-partition
drift blocks the joint decision.  Risk reduction remains exempt after every
source is exactly verified.  No runtime, order, paper, or live authority exists.
"""

from __future__ import annotations

import copy
import hmac
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v2 as weighted_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-stability-preregistration-v1"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-cluster-multi-window-stability-gate-v1"
)
VERIFICATION_SCHEMA_VERSION = f"{GATE_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-correlation-cluster-multi-window-stability-gate-lock-1"
)
WEIGHTED_V2_IMPLEMENTATION_SHA256 = (
    "1832e4dede892c8d5748a829cd39562773c425e0ce7c970b584538ade7c3adfe"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
WINDOW_AGGREGATION_POLICY = "ANY_EXACT_WINDOW_BLOCKS_RISK_INCREASE"
PARTITION_STABILITY_POLICY = (
    "REQUIRE_IDENTICAL_COMPLETE_LINK_PARTITION_FOR_RISK_INCREASE"
)
REQUIRED_WINDOW_COUNT = 3
WINDOW_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "preregistration",
        "correlation_matrix",
        "complete_link_audit",
        "equity",
        "positions",
        "proposed_symbol",
        "proposed_notional",
        "proposed_direction",
        "max_cluster_gross_pct",
        "risk_increasing",
    }
)

_VERIFY_WEIGHTED_V2 = (
    weighted_v2.verify_strategy_correlation_cluster_effective_bet_budget_v2
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOW_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")


class MultiWindowStabilityContractError(ValueError):
    """Raised when preregistration cannot be made deterministic."""


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _sealed_hash_exact(document: Any, field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(field)):
        return False
    unhashed = copy.deepcopy(document)
    supplied = unhashed.pop(field)
    try:
        expected = strict_canonical_hash(unhashed)
    except ValueError:
        return False
    return hmac.compare_digest(supplied, expected)


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    return (
        type(authority) is dict
        and bool(authority)
        and authority.get("descriptive_only") is True
        and all(type(value) is bool for value in authority.values())
        and all(
            value is False
            for key, value in authority.items()
            if key != "descriptive_only"
        )
    )


def _validate_window_specs(window_specs: Any) -> list[dict[str, Any]]:
    if type(window_specs) is not list or len(window_specs) != REQUIRED_WINDOW_COUNT:
        raise MultiWindowStabilityContractError(
            f"window_specs must contain exactly {REQUIRED_WINDOW_COUNT} windows"
        )
    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    previous_lookback = 0
    for item in window_specs:
        if type(item) is not dict or set(item) != {
            "window_id",
            "lookback_observations",
        }:
            raise MultiWindowStabilityContractError(
                "each window spec must have exact keys"
            )
        window_id = item["window_id"]
        lookback = item["lookback_observations"]
        if type(window_id) is not str or _WINDOW_ID_RE.fullmatch(window_id) is None:
            raise MultiWindowStabilityContractError("window_id is invalid")
        if window_id in ids:
            raise MultiWindowStabilityContractError("window_id must be unique")
        if (
            type(lookback) is not int
            or type(lookback) is bool
            or lookback < 20
            or lookback <= previous_lookback
        ):
            raise MultiWindowStabilityContractError(
                "lookbacks must be integers >= 20 in strictly increasing order"
            )
        ids.add(window_id)
        previous_lookback = lookback
        normalized.append(
            {"window_id": window_id, "lookback_observations": lookback}
        )
    return normalized


def build_strategy_correlation_cluster_multi_window_stability_preregistration_v1(
    window_specs: Any,
) -> dict[str, Any]:
    """Freeze the exact windows and conservative aggregation policy."""

    specs = _validate_window_specs(window_specs)
    return seal_strict_canonical_document(
        {
            "schema_version": PREREGISTRATION_SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "PREREGISTERED_RESEARCH_ONLY",
            "window_specs": specs,
            "required_window_count": REQUIRED_WINDOW_COUNT,
            "window_aggregation_policy": WINDOW_AGGREGATION_POLICY,
            "partition_stability_policy": PARTITION_STABILITY_POLICY,
            "risk_reduction_exemption": True,
            "implementation_pins": {
                "weighted_budget_v2": WEIGHTED_V2_IMPLEMENTATION_SHA256,
                "strict_canonical_json_hash": (
                    STRICT_CANONICAL_IMPLEMENTATION_SHA256
                ),
            },
            "facts": {
                "windows_selected_before_evaluation": True,
                "window_data_observed_by_builder": False,
                "runtime_assets_accessed": False,
                "profitability_proven": False,
            },
            "authority": _authority(),
        },
        "preregistration_hash",
    )


def verify_strategy_correlation_cluster_multi_window_stability_preregistration_v1(
    document: Any,
    window_specs: Any,
    *,
    expected_preregistration_hash: Any,
) -> bool:
    """Verify the preregistration against an out-of-band expected hash."""

    if not _same_hash(
        document.get("preregistration_hash") if type(document) is dict else None,
        expected_preregistration_hash,
    ):
        return False
    try:
        rebuilt = build_strategy_correlation_cluster_multi_window_stability_preregistration_v1(
            window_specs
        )
    except (MultiWindowStabilityContractError, TypeError, ValueError):
        return False
    return type(document) is dict and strict_json_contract_equal(document, rebuilt)


def _preregistration_presentable(
    preregistration: Any, expected_preregistration_hash: Any
) -> bool:
    if (
        type(preregistration) is not dict
        or preregistration.get("schema_version") != PREREGISTRATION_SCHEMA_VERSION
        or preregistration.get("static_fingerprint") != STATIC_FINGERPRINT
        or preregistration.get("status") != "PREREGISTERED_RESEARCH_ONLY"
        or preregistration.get("required_window_count") != REQUIRED_WINDOW_COUNT
        or preregistration.get("window_aggregation_policy")
        != WINDOW_AGGREGATION_POLICY
        or preregistration.get("partition_stability_policy")
        != PARTITION_STABILITY_POLICY
        or preregistration.get("risk_reduction_exemption") is not True
        or not _same_hash(
            preregistration.get("preregistration_hash"),
            expected_preregistration_hash,
        )
        or not _sealed_hash_exact(preregistration, "preregistration_hash")
        or not _authority_locked(preregistration)
    ):
        return False
    pins = preregistration.get("implementation_pins")
    facts = preregistration.get("facts")
    try:
        specs = _validate_window_specs(preregistration.get("window_specs"))
    except MultiWindowStabilityContractError:
        return False
    return (
        specs == preregistration["window_specs"]
        and pins
        == {
            "weighted_budget_v2": WEIGHTED_V2_IMPLEMENTATION_SHA256,
            "strict_canonical_json_hash": STRICT_CANONICAL_IMPLEMENTATION_SHA256,
        }
        and type(facts) is dict
        and facts.get("windows_selected_before_evaluation") is True
        and facts.get("window_data_observed_by_builder") is False
        and facts.get("runtime_assets_accessed") is False
        and facts.get("profitability_proven") is False
    )


def _context_valid(context: Any) -> bool:
    if type(context) is not dict or frozenset(context) != WINDOW_VERIFICATION_CONTEXT_KEYS:
        return False
    dict_fields = {
        "preregistration",
        "correlation_matrix",
        "complete_link_audit",
    }
    return (
        all(type(context[field]) is dict for field in dict_fields)
        and type(context["positions"]) is list
        and type(context["proposed_symbol"]) is str
        and type(context["proposed_direction"]) is str
        and type(context["risk_increasing"]) is bool
    )


def _weighted_receipt_passed(receipt: Any, expected_decision: Any) -> bool:
    return (
        type(receipt) is dict
        and receipt.get("status") == "PASS"
        and receipt.get("blockers") == []
        and receipt.get("budget_decision") == expected_decision
        and receipt.get("runtime_gate_activation_allowed") is False
        and receipt.get("current_admission_allowed") is False
        and receipt.get("paper_authorized") is False
        and receipt.get("live_order_allowed") is False
    )


def _call_weighted_verifier(document: Any, context: Any) -> bool:
    if not _context_valid(context):
        return False
    try:
        receipt = _VERIFY_WEIGHTED_V2(
            copy.deepcopy(document),
            copy.deepcopy(context["preregistration"]),
            copy.deepcopy(context["correlation_matrix"]),
            copy.deepcopy(context["complete_link_audit"]),
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
    return _weighted_receipt_passed(
        receipt,
        document.get("decision") if type(document) is dict else None,
    )


def _weighted_document_presentable(document: Any, context: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != weighted_v2.BUDGET_SCHEMA_VERSION
        or document.get("static_fingerprint") != weighted_v2.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or type(document.get("decision")) is not str
        or not document["decision"]
        or not _sealed_hash_exact(document, "budget_v2_hash")
        or not _authority_locked(document)
    ):
        return False
    facts = document.get("facts")
    checks = document.get("checks")
    blockers = document.get("blockers")
    if (
        type(facts) is not dict
        or type(checks) is not list
        or not checks
        or type(blockers) is not list
    ):
        return False
    if any(
        type(item) is not dict
        or type(item.get("blocking")) is not bool
        or type(item.get("ok")) is not bool
        for item in checks
    ):
        return False
    blocking_failures = [
        item for item in checks if item["blocking"] and not item["ok"]
    ]
    status_consistent = (
        document["status"] == "PASS" and not blocking_failures
    ) or (document["status"] == "BLOCK" and bool(blocking_failures))
    return (
        status_consistent
        and facts.get("risk_increasing") is context.get("risk_increasing")
        and facts.get("weighted_metrics_exactly_derived") is True
        and facts.get("source_documents_embedded") is False
        and facts.get("runtime_assets_accessed") is False
        and facts.get("runtime_gate_integrated") is False
        and facts.get("profitability_proven") is False
    )


def _matrix_and_partition(
    context: dict[str, Any], expected_lookback: int
) -> tuple[str, tuple[tuple[str, ...], ...]] | None:
    matrix = context["correlation_matrix"]
    audit = context["complete_link_audit"]
    if (
        matrix.get("schema_version") != "strategy-selection-correlation-matrix-v1"
        or matrix.get("status") != "PASS"
        or matrix.get("lookback_observations") != expected_lookback
        or not _is_hash(matrix.get("matrix_hash"))
        or type(matrix.get("symbols")) is not list
        or not matrix["symbols"]
        or len(set(matrix["symbols"])) != len(matrix["symbols"])
        or audit.get("schema_version")
        != "strategy-correlation-cluster-complete-link-audit-v1"
        or audit.get("status") != "PASS"
        or not _same_hash(audit.get("matrix_hash"), matrix["matrix_hash"])
        or type(audit.get("cluster_results")) is not list
    ):
        return None
    permissions = matrix.get("permissions")
    audit_permissions = audit.get("permissions")
    if (
        type(permissions) is not dict
        or permissions.get("paper_authorized") is not False
        or permissions.get("live_order_allowed") is not False
        or type(audit_permissions) is not dict
        or audit_permissions.get("paper_authorized") is not False
        or audit_permissions.get("live_order_allowed") is not False
    ):
        return None
    clusters: list[tuple[str, ...]] = []
    seen: set[str] = set()
    for cluster in audit["cluster_results"]:
        members = cluster.get("members") if type(cluster) is dict else None
        if (
            type(members) is not list
            or not members
            or any(type(member) is not str or not member for member in members)
            or len(set(members)) != len(members)
            or seen.intersection(members)
        ):
            return None
        seen.update(members)
        clusters.append(tuple(sorted(members)))
    if seen != set(matrix["symbols"]):
        return None
    return matrix["matrix_hash"], tuple(sorted(clusters))


def _identity_payload(context: dict[str, Any]) -> dict[str, Any]:
    matrix = context["correlation_matrix"]
    preregistration = context["preregistration"]
    audit = context["complete_link_audit"]
    return {
        "equity": copy.deepcopy(context["equity"]),
        "positions": copy.deepcopy(context["positions"]),
        "proposed_symbol": context["proposed_symbol"],
        "proposed_notional": copy.deepcopy(context["proposed_notional"]),
        "proposed_direction": context["proposed_direction"],
        "max_cluster_gross_pct": copy.deepcopy(
            context["max_cluster_gross_pct"]
        ),
        "risk_increasing": context["risk_increasing"],
        "matrix_symbols": copy.deepcopy(matrix.get("symbols")),
        "preregistration_symbols": copy.deepcopy(
            preregistration.get("symbols")
        ),
        "return_series": matrix.get("return_series"),
        "absolute_pearson_threshold": audit.get(
            "absolute_pearson_threshold"
        ),
    }


def _evaluate_sources(
    specs: list[dict[str, Any]],
    window_budget_documents: Any,
    window_verification_contexts: Any,
) -> tuple[list[dict[str, Any]], bool, bool, bool, str | None]:
    window_ids = [item["window_id"] for item in specs]
    if (
        type(window_budget_documents) is not dict
        or type(window_verification_contexts) is not dict
        or set(window_budget_documents) != set(window_ids)
        or set(window_verification_contexts) != set(window_ids)
    ):
        return [], False, False, False, None
    summaries: list[dict[str, Any]] = []
    matrix_hashes: set[str] = set()
    partition_hashes: list[str] = []
    identity_hash: str | None = None
    risk_increasing: bool | None = None
    for spec in specs:
        window_id = spec["window_id"]
        document = window_budget_documents[window_id]
        context = window_verification_contexts[window_id]
        if (
            not _context_valid(context)
            or not _call_weighted_verifier(document, context)
            or not _weighted_document_presentable(document, context)
        ):
            return [], False, False, False, None
        matrix_partition = _matrix_and_partition(
            context, spec["lookback_observations"]
        )
        if matrix_partition is None:
            return [], False, False, False, None
        matrix_hash, partition = matrix_partition
        if matrix_hash in matrix_hashes:
            return [], False, False, False, None
        matrix_hashes.add(matrix_hash)
        current_identity_hash = strict_canonical_hash(_identity_payload(context))
        if identity_hash is None:
            identity_hash = current_identity_hash
            risk_increasing = context["risk_increasing"]
        elif not hmac.compare_digest(identity_hash, current_identity_hash):
            return [], False, False, False, None
        partition_hash = strict_canonical_hash(
            {"complete_link_partition": [list(cluster) for cluster in partition]}
        )
        partition_hashes.append(partition_hash)
        summaries.append(
            {
                "window_id": window_id,
                "lookback_observations": spec["lookback_observations"],
                "matrix_hash": matrix_hash,
                "budget_v2_hash": document["budget_v2_hash"],
                "budget_status": document["status"],
                "budget_decision": document["decision"],
                "cluster_count": len(partition),
                "cluster_partition_hash": partition_hash,
                "weighted_budget_exactly_verified": True,
            }
        )
    partition_stable = len(set(partition_hashes)) == 1
    any_window_blocked = any(
        item["budget_status"] == "BLOCK" or item["budget_decision"] == "BLOCK"
        for item in summaries
    )
    return (
        summaries,
        True,
        partition_stable,
        any_window_blocked,
        identity_hash if type(risk_increasing) is bool else None,
    )


def evaluate_strategy_correlation_cluster_multi_window_stability_gate_v1(
    preregistration: Any,
    window_budget_documents: Any,
    *,
    window_verification_contexts: Any,
    expected_preregistration_hash: Any,
) -> dict[str, Any]:
    """Evaluate registered windows without embedding matrices or positions."""

    preregistration_exact = _preregistration_presentable(
        preregistration, expected_preregistration_hash
    )
    specs = (
        copy.deepcopy(preregistration["window_specs"])
        if preregistration_exact
        else []
    )
    summaries, sources_exact, partition_stable, any_blocked, identity_hash = (
        _evaluate_sources(specs, window_budget_documents, window_verification_contexts)
        if preregistration_exact
        else ([], False, False, False, None)
    )
    known = preregistration_exact and sources_exact and _is_hash(identity_hash)
    risk_increasing = (
        window_verification_contexts[specs[0]["window_id"]]["risk_increasing"]
        if known
        else None
    )
    if not known:
        status = "UNKNOWN"
        decision = "BLOCK_MULTI_WINDOW_SOURCE_UNVERIFIED"
        blockers = ["multi_window_source_verification"]
    elif risk_increasing and any_blocked:
        status = "BLOCK"
        decision = "BLOCK_REGISTERED_WINDOW_WEIGHTED_BUDGET"
        blockers = ["registered_window_weighted_budget_block"]
    elif risk_increasing and not partition_stable:
        status = "BLOCK"
        decision = "BLOCK_REGISTERED_WINDOW_CLUSTER_PARTITION_DRIFT"
        blockers = ["registered_window_cluster_partition_drift"]
    elif risk_increasing:
        status = "PASS"
        decision = "PASS_MULTI_WINDOW_STABLE_RESEARCH_GATE"
        blockers = []
    else:
        status = "PASS"
        decision = "PASS_RISK_REDUCTION_MULTI_WINDOW_EXEMPT"
        blockers = []
    decision_pairs = {
        (item["budget_status"], item["budget_decision"])
        for item in summaries
    }
    document = {
        "schema_version": GATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": decision,
        "source": {
            "preregistration_hash": (
                preregistration.get("preregistration_hash")
                if preregistration_exact
                else None
            ),
            "trade_identity_hash": identity_hash,
            "weighted_v2_implementation_sha256": (
                WEIGHTED_V2_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "source_documents_embedded": False,
            "verification_contexts_embedded": False,
        },
        "window_summaries": summaries,
        "summary": {
            "registered_window_count": len(specs) if preregistration_exact else 0,
            "verified_window_count": len(summaries),
            "unique_matrix_hash_count": (
                len({item["matrix_hash"] for item in summaries})
            ),
            "unique_partition_count": (
                len({item["cluster_partition_hash"] for item in summaries})
            ),
            "window_budget_decision_variant_count": len(decision_pairs),
            "risk_increasing": risk_increasing,
            "any_registered_window_blocked": any_blocked if known else False,
            "cluster_partition_stable": partition_stable if known else False,
        },
        "facts": {
            "preregistration_exactly_verified": preregistration_exact,
            "all_registered_windows_exactly_verified": known,
            "trade_identity_consistent_across_windows": known,
            "matrix_hashes_unique_across_windows": known,
            "cluster_partition_stable": partition_stable if known else False,
            "any_registered_window_blocked": any_blocked if known else False,
            "single_window_independence_assumption_used": False,
            "risk_reduction_exemption_applied": known and risk_increasing is False,
            "correlation_matrices_embedded": False,
            "complete_link_audits_embedded": False,
            "positions_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_gate_integrated": False,
            "profitability_proven": False,
        },
        "blockers": blockers,
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "stability_gate_hash")


def verify_strategy_correlation_cluster_multi_window_stability_gate_v1(
    document: Any,
    preregistration: Any,
    window_budget_documents: Any,
    *,
    window_verification_contexts: Any,
    expected_preregistration_hash: Any,
) -> dict[str, Any]:
    """Rebuild every source and return a non-authorizing receipt."""

    try:
        rebuilt = evaluate_strategy_correlation_cluster_multi_window_stability_gate_v1(
            preregistration,
            window_budget_documents,
            window_verification_contexts=window_verification_contexts,
            expected_preregistration_hash=expected_preregistration_hash,
        )
        exact = (
            type(document) is dict
            and strict_json_contract_equal(document, rebuilt)
            and document.get("schema_version") == GATE_SCHEMA_VERSION
            and document.get("status") in {"PASS", "BLOCK"}
            and _sealed_hash_exact(document, "stability_gate_hash")
            and _authority_locked(document)
        )
    except Exception:
        exact = False
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "stability_gate_exactly_verified": exact,
        "stability_gate_decision": (
            document.get("decision") if exact and type(document) is dict else "UNKNOWN"
        ),
        "blockers": [] if exact else ["multi_window_stability_exact_rebuild"],
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "GATE_SCHEMA_VERSION",
    "MultiWindowStabilityContractError",
    "PARTITION_STABILITY_POLICY",
    "PREREGISTRATION_SCHEMA_VERSION",
    "REQUIRED_WINDOW_COUNT",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "VERIFICATION_SCHEMA_VERSION",
    "WEIGHTED_V2_IMPLEMENTATION_SHA256",
    "WINDOW_AGGREGATION_POLICY",
    "WINDOW_VERIFICATION_CONTEXT_KEYS",
    "build_strategy_correlation_cluster_multi_window_stability_preregistration_v1",
    "evaluate_strategy_correlation_cluster_multi_window_stability_gate_v1",
    "verify_strategy_correlation_cluster_multi_window_stability_gate_v1",
    "verify_strategy_correlation_cluster_multi_window_stability_preregistration_v1",
]
