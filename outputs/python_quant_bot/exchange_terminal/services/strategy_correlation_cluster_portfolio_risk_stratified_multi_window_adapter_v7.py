"""Anchor adapter joining budget-v3 to multi-window stratified gate-v2.

The adapter exactly verifies both immutable components and proves that one
registered anchor window uses the same budget-v3 document and verification
context supplied to the adapter. A single-window PASS cannot override a
multi-window BLOCK. No runtime, current, paper, live, or order authority exists.
"""

from __future__ import annotations

import copy
import hmac
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v3 as budget_v3,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_multi_window_stratified_stability_gate_v2
    as stability_v2,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-stratified-"
    "multi-window-adapter-v7"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-stratified-multi-window-anchor-adapter-v7-lock-1"
)
BUDGET_V3_IMPLEMENTATION_SHA256 = (
    "bece44fe40c02242c879d1dead5cc11d2ce00edfc91c8d78a5b29962516c002d"
)
STABILITY_GATE_V2_IMPLEMENTATION_SHA256 = (
    "0756cc0d0338170e80bd2b3672ecd6a65542953e2c0dc92a48c05229e0f7902f"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
ANCHOR_BUDGET_VERIFICATION_CONTEXT_KEYS = stability_v2.WINDOW_VERIFICATION_CONTEXT_KEYS
STABILITY_GATE_VERIFICATION_CONTEXT_KEYS = frozenset(
    {
        "anchor_window_id",
        "expected_preregistration_v2_hash",
        "preregistration",
        "risk_increasing",
        "window_budget_v3_documents",
        "window_verification_contexts",
    }
)

_VERIFY_BUDGET_V3 = budget_v3.verify_strategy_correlation_cluster_effective_bet_budget_v3
_VERIFY_STABILITY_GATE_V2 = (
    stability_v2.verify_strategy_correlation_cluster_multi_window_stratified_stability_gate_v2
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_BUDGET_RECEIPT_KEYS = {
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
_GATE_RECEIPT_KEYS = {
    "blockers",
    "current_admission_allowed",
    "live_order_allowed",
    "paper_authorized",
    "runtime_gate_activation_allowed",
    "schema_version",
    "stability_gate_decision",
    "stability_gate_exactly_verified",
    "stability_gate_status",
    "stability_gate_v2_hash",
    "status",
    "writer_allowed",
}


def _exact_keys(value: Any, expected: set[str] | frozenset[str]) -> bool:
    return type(value) is dict and set(value) == set(expected)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _same_hash(left: Any, right: Any) -> bool:
    return _is_hash(left) and _is_hash(right) and hmac.compare_digest(left, right)


def _sealed_hash_exact(document: Any, field: str) -> bool:
    if type(document) is not dict or not _is_hash(document.get(field)):
        return False
    body = copy.deepcopy(document)
    supplied = body.pop(field)
    try:
        expected = strict_canonical_hash(body)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(supplied, expected)


def _descriptive_authority_locked(document: Any) -> bool:
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


def _adapter_authority_locked(document: Any) -> bool:
    authority = document.get("authority") if type(document) is dict else None
    if type(authority) is not dict or not authority:
        return False
    for key, value in authority.items():
        if type(key) is not str or type(value) is not bool:
            return False
        if key in {"local_decision_only", "research_only"}:
            if value is not True:
                return False
        elif value is not False:
            return False
    return True


def _authority() -> dict[str, bool]:
    return {
        "local_decision_only": True,
        "research_only": True,
        "writer_allowed": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "formal_registry_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _budget_context_valid(context: Any) -> bool:
    if not _exact_keys(context, ANCHOR_BUDGET_VERIFICATION_CONTEXT_KEYS):
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
        and context["risk_increasing"] is True
    )


def _stability_context_valid(context: Any) -> bool:
    return (
        _exact_keys(context, STABILITY_GATE_VERIFICATION_CONTEXT_KEYS)
        and type(context["anchor_window_id"]) is str
        and bool(context["anchor_window_id"])
        and _is_hash(context["expected_preregistration_v2_hash"])
        and type(context["preregistration"]) is dict
        and type(context["window_budget_v3_documents"]) is dict
        and type(context["window_verification_contexts"]) is dict
        and context["risk_increasing"] is True
    )


def _budget_receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(receipt, _BUDGET_RECEIPT_KEYS)
        and receipt["schema_version"] == budget_v3.BUDGET_VERIFICATION_SCHEMA_VERSION
        and receipt["status"] == "PASS"
        and receipt["budget_decision"] == document.get("decision")
        and receipt["budget_v3_hash"] == document.get("budget_v3_hash")
        and receipt["writer_allowed"] is False
        and receipt["runtime_gate_activation_allowed"] is False
        and receipt["current_admission_allowed"] is False
        and receipt["paper_authorized"] is False
        and receipt["live_order_allowed"] is False
    )


def _gate_receipt_valid(receipt: Any, document: Any) -> bool:
    return (
        _exact_keys(receipt, _GATE_RECEIPT_KEYS)
        and receipt["schema_version"] == stability_v2.VERIFICATION_SCHEMA_VERSION
        and receipt["status"] == "PASS"
        and receipt["stability_gate_exactly_verified"] is True
        and receipt["stability_gate_status"] == document.get("status")
        and receipt["stability_gate_decision"] == document.get("decision")
        and receipt["stability_gate_v2_hash"] == document.get("stability_gate_v2_hash")
        and receipt["blockers"] == []
        and receipt["writer_allowed"] is False
        and receipt["runtime_gate_activation_allowed"] is False
        and receipt["current_admission_allowed"] is False
        and receipt["paper_authorized"] is False
        and receipt["live_order_allowed"] is False
    )


def _call_budget_verifier(document: Any, context: Any) -> bool:
    if not _budget_context_valid(context):
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
            max_cluster_gross_pct=copy.deepcopy(context["max_cluster_gross_pct"]),
            risk_increasing=True,
        )
    except Exception:
        return False
    return _budget_receipt_valid(receipt, document)


def _call_gate_verifier(document: Any, context: Any) -> bool:
    if not _stability_context_valid(context):
        return False
    try:
        receipt = _VERIFY_STABILITY_GATE_V2(
            copy.deepcopy(document),
            copy.deepcopy(context["preregistration"]),
            copy.deepcopy(context["window_budget_v3_documents"]),
            window_verification_contexts=copy.deepcopy(
                context["window_verification_contexts"]
            ),
            expected_preregistration_v2_hash=context[
                "expected_preregistration_v2_hash"
            ],
            risk_increasing=True,
        )
    except Exception:
        return False
    return _gate_receipt_valid(receipt, document)


def _budget_presentable(document: Any) -> bool:
    blockers = document.get("blockers") if type(document) is dict else None
    return (
        type(document) is dict
        and document.get("schema_version") == budget_v3.BUDGET_SCHEMA_VERSION
        and document.get("static_fingerprint") == budget_v3.STATIC_FINGERPRINT
        and document.get("status") in {"PASS", "BLOCK"}
        and type(document.get("decision")) is str
        and bool(document["decision"])
        and _sealed_hash_exact(document, "budget_v3_hash")
        and _descriptive_authority_locked(document)
        and type(blockers) is list
        and all(type(item) is str for item in blockers)
        and (
            (document["status"] == "PASS" and blockers == [])
            or (document["status"] == "BLOCK" and bool(blockers))
        )
        and type(document.get("facts")) is dict
        and document["facts"].get("risk_increasing") is True
    )


def _gate_presentable(document: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != stability_v2.GATE_SCHEMA_VERSION
        or document.get("static_fingerprint") != stability_v2.STATIC_FINGERPRINT
        or document.get("status") not in {"PASS", "BLOCK"}
        or not _sealed_hash_exact(document, "stability_gate_v2_hash")
        or not _descriptive_authority_locked(document)
    ):
        return False
    source = document.get("source")
    facts = document.get("facts")
    summaries = document.get("window_summaries")
    blockers = document.get("blockers")
    return (
        type(source) is dict
        and _is_hash(source.get("preregistration_v2_hash"))
        and _is_hash(source.get("trade_identity_hash"))
        and source.get("source_documents_embedded") is False
        and source.get("verification_contexts_embedded") is False
        and type(facts) is dict
        and facts.get("preregistration_exactly_verified") is True
        and facts.get("all_registered_windows_exactly_verified") is True
        and facts.get("trade_identity_consistent_across_windows") is True
        and facts.get("matrix_hashes_unique_across_windows") is True
        and facts.get("single_window_independence_assumption_used") is False
        and facts.get("source_documents_embedded") is False
        and facts.get("verification_contexts_embedded") is False
        and facts.get("positions_embedded") is False
        and facts.get("runtime_assets_accessed") is False
        and facts.get("runtime_gate_integrated") is False
        and facts.get("profitability_proven") is False
        and type(summaries) is list
        and len(summaries) == stability_v2.REQUIRED_WINDOW_COUNT
        and type(blockers) is list
        and (
            (document["status"] == "PASS" and blockers == [])
            or (document["status"] == "BLOCK" and bool(blockers))
        )
    )


def _trade_identity_hash(context: Any) -> str | None:
    if not _budget_context_valid(context):
        return None
    matrix = context["correlation_matrix"]
    source_preregistration = context["preregistration"]
    audit = context["complete_link_audit"]
    try:
        return strict_canonical_hash(
            {
                "absolute_pearson_threshold": audit.get(
                    "absolute_pearson_threshold"
                ),
                "equity": copy.deepcopy(context["equity"]),
                "matrix_symbols": copy.deepcopy(matrix.get("symbols")),
                "max_cluster_gross_pct": copy.deepcopy(
                    context["max_cluster_gross_pct"]
                ),
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
        )
    except (TypeError, ValueError):
        return None


def _cross_bindings(
    anchor_document: Any,
    gate_document: Any,
    anchor_context: Any,
    gate_context: Any,
) -> dict[str, bool]:
    anchor_id = (
        gate_context.get("anchor_window_id") if type(gate_context) is dict else None
    )
    window_documents = (
        gate_context.get("window_budget_v3_documents")
        if type(gate_context) is dict
        else None
    )
    window_contexts = (
        gate_context.get("window_verification_contexts")
        if type(gate_context) is dict
        else None
    )
    summaries = (
        gate_document.get("window_summaries")
        if type(gate_document) is dict
        else None
    )
    matches = (
        [
            item
            for item in summaries
            if type(item) is dict and item.get("window_id") == anchor_id
        ]
        if type(summaries) is list
        else []
    )
    anchor_summary = matches[0] if len(matches) == 1 else None
    gate_anchor_document = (
        window_documents.get(anchor_id)
        if type(window_documents) is dict and type(anchor_id) is str
        else None
    )
    gate_anchor_context = (
        window_contexts.get(anchor_id)
        if type(window_contexts) is dict and type(anchor_id) is str
        else None
    )
    gate_source = gate_document.get("source") if type(gate_document) is dict else None
    gate_preregistration = (
        gate_context.get("preregistration") if type(gate_context) is dict else None
    )
    window_specs = (
        gate_preregistration.get("window_specs")
        if type(gate_preregistration) is dict
        else None
    )
    spec_matches = (
        [
            item
            for item in window_specs
            if type(item) is dict and item.get("window_id") == anchor_id
        ]
        if type(window_specs) is list
        else []
    )
    return {
        "anchor_window_present_once": len(matches) == 1,
        "anchor_window_spec_present_once": len(spec_matches) == 1,
        "anchor_budget_document_exact_identity": (
            type(anchor_document) is dict
            and type(gate_anchor_document) is dict
            and strict_json_contract_equal(anchor_document, gate_anchor_document)
        ),
        "anchor_budget_context_exact_identity": (
            type(anchor_context) is dict
            and type(gate_anchor_context) is dict
            and strict_json_contract_equal(anchor_context, gate_anchor_context)
        ),
        "anchor_budget_hash_identity": (
            type(anchor_summary) is dict
            and _same_hash(
                anchor_document.get("budget_v3_hash")
                if type(anchor_document) is dict
                else None,
                anchor_summary.get("budget_v3_hash"),
            )
        ),
        "anchor_status_identity": (
            type(anchor_summary) is dict
            and type(anchor_document) is dict
            and anchor_summary.get("budget_status") == anchor_document.get("status")
        ),
        "anchor_decision_identity": (
            type(anchor_summary) is dict
            and type(anchor_document) is dict
            and anchor_summary.get("budget_decision")
            == anchor_document.get("decision")
        ),
        "anchor_lookback_identity": (
            type(anchor_summary) is dict
            and len(spec_matches) == 1
            and anchor_summary.get("lookback_observations")
            == spec_matches[0].get("lookback_observations")
        ),
        "trade_identity_hash_identity": (
            type(gate_source) is dict
            and _same_hash(
                _trade_identity_hash(anchor_context),
                gate_source.get("trade_identity_hash"),
            )
        ),
        "preregistration_hash_identity": (
            type(gate_source) is dict
            and type(gate_context) is dict
            and _same_hash(
                gate_source.get("preregistration_v2_hash"),
                gate_context.get("expected_preregistration_v2_hash"),
            )
        ),
    }


def _checks(
    anchor_document: Any,
    gate_document: Any,
    *,
    anchor_context: Any,
    gate_context: Any,
) -> dict[str, bool]:
    checks = {
        "anchor_budget_context_exact": _budget_context_valid(anchor_context),
        "stability_gate_context_exact": _stability_context_valid(gate_context),
        "anchor_budget_exactly_verified": _call_budget_verifier(
            anchor_document, anchor_context
        ),
        "stability_gate_exactly_verified": _call_gate_verifier(
            gate_document, gate_context
        ),
        "anchor_budget_presentable": _budget_presentable(anchor_document),
        "stability_gate_presentable": _gate_presentable(gate_document),
    }
    checks.update(
        _cross_bindings(anchor_document, gate_document, anchor_context, gate_context)
    )
    return checks


def evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7(
    anchor_budget_v3_document: Any,
    stability_gate_v2_document: Any,
    *,
    anchor_budget_v3_verification_context: Any,
    stability_gate_v2_verification_context: Any,
    risk_increasing: Any,
) -> dict[str, Any]:
    """Build a summary-only local decision from exact immutable components."""
    risk_flag = risk_increasing if type(risk_increasing) is bool else None
    if risk_flag is False:
        checks: dict[str, bool] = {}
        known = False
        status = "PASS"
        decision = "PASS_RISK_REDUCTION_SOURCE_FREE"
        blockers: list[str] = []
        anchor_status = "NOT_REQUIRED"
        gate_status = "NOT_REQUIRED"
    else:
        checks = _checks(
            anchor_budget_v3_document,
            stability_gate_v2_document,
            anchor_context=anchor_budget_v3_verification_context,
            gate_context=stability_gate_v2_verification_context,
        ) if risk_flag is True else {}
        known = risk_flag is True and bool(checks) and all(checks.values())
        anchor_status = (
            anchor_budget_v3_document.get("status")
            if known and type(anchor_budget_v3_document) is dict
            else "UNKNOWN"
        )
        gate_status = (
            stability_gate_v2_document.get("status")
            if known and type(stability_gate_v2_document) is dict
            else "UNKNOWN"
        )
        if not known:
            status = "UNKNOWN"
            decision = "BLOCK_STRATIFIED_MULTI_WINDOW_JOINT_SOURCE_UNVERIFIED"
            blockers = ["stratified_multi_window_anchor_exact_source_closure"]
        elif anchor_status == "BLOCK":
            status = "BLOCK"
            decision = "BLOCK_ANCHOR_STRATIFIED_BUDGET_COMPONENT"
            blockers = ["anchor_stratified_budget_component_block"]
        elif gate_status == "BLOCK":
            status = "BLOCK"
            decision = "BLOCK_MULTI_WINDOW_STRATIFIED_STABILITY_COMPONENT"
            blockers = ["multi_window_stratified_stability_component_block"]
        else:
            status = "PASS"
            decision = "PASS_ANCHOR_AND_MULTI_WINDOW_STRATIFIED_RESEARCH_GATE"
            blockers = []

    anchor_id = (
        stability_gate_v2_verification_context.get("anchor_window_id")
        if known and type(stability_gate_v2_verification_context) is dict
        else None
    )
    gate_source = (
        stability_gate_v2_document.get("source")
        if known and type(stability_gate_v2_document) is dict
        else None
    )
    document = {
        "authority": _authority(),
        "blockers": blockers,
        "checks": checks,
        "component_states": {
            "anchor_budget_v3_decision": (
                anchor_budget_v3_document.get("decision")
                if known and type(anchor_budget_v3_document) is dict
                else anchor_status
            ),
            "anchor_budget_v3_status": anchor_status,
            "stability_gate_v2_decision": (
                stability_gate_v2_document.get("decision")
                if known and type(stability_gate_v2_document) is dict
                else gate_status
            ),
            "stability_gate_v2_status": gate_status,
        },
        "decision": decision,
        "facts": {
            "anchor_budget_and_context_cross_bound": known,
            "anchor_budget_v3_exactly_verified": known,
            "correlation_matrices_embedded": False,
            "joint_local_research_decision_made": known,
            "multi_window_block_overrides_anchor_pass": True,
            "positions_embedded": False,
            "profitability_proven": False,
            "risk_reduction_source_free": risk_flag is False,
            "risk_service_invoked": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
            "source_documents_embedded": False,
            "stability_gate_v2_exactly_verified": known,
            "trade_identity_cross_bound": known,
            "verification_contexts_embedded": False,
        },
        "schema_version": SCHEMA_VERSION,
        "source": {
            "anchor_budget_v3_hash": (
                anchor_budget_v3_document.get("budget_v3_hash")
                if known and type(anchor_budget_v3_document) is dict
                else None
            ),
            "anchor_window_id": anchor_id,
            "budget_v3_implementation_sha256": BUDGET_V3_IMPLEMENTATION_SHA256,
            "source_documents_embedded": False,
            "stability_gate_v2_hash": (
                stability_gate_v2_document.get("stability_gate_v2_hash")
                if known and type(stability_gate_v2_document) is dict
                else None
            ),
            "stability_gate_v2_implementation_sha256": (
                STABILITY_GATE_V2_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "trade_identity_hash": (
                gate_source.get("trade_identity_hash")
                if type(gate_source) is dict
                else None
            ),
            "verification_contexts_embedded": False,
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
    }
    return seal_strict_canonical_document(document, "adapter_v7_hash")


def verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7(
    document: Any,
    anchor_budget_v3_document: Any,
    stability_gate_v2_document: Any,
    *,
    anchor_budget_v3_verification_context: Any,
    stability_gate_v2_verification_context: Any,
    risk_increasing: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7(
            anchor_budget_v3_document,
            stability_gate_v2_document,
            anchor_budget_v3_verification_context=(
                anchor_budget_v3_verification_context
            ),
            stability_gate_v2_verification_context=(
                stability_gate_v2_verification_context
            ),
            risk_increasing=risk_increasing,
        )
        exact = (
            type(document) is dict
            and strict_json_contract_equal(document, expected)
            and document.get("schema_version") == SCHEMA_VERSION
            and document.get("status") in {"PASS", "BLOCK"}
            and _sealed_hash_exact(document, "adapter_v7_hash")
            and _adapter_authority_locked(document)
        )
    except Exception:
        exact = False
    return {
        "adapter_v7_exactly_verified": exact,
        "adapter_v7_hash": (
            document.get("adapter_v7_hash")
            if exact and type(document) is dict
            else None
        ),
        "adapter_v7_status": (
            document.get("status") if exact and type(document) is dict else "UNKNOWN"
        ),
        "blockers": [] if exact else ["stratified_multi_window_adapter_v7_exact_rebuild"],
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "risk_service_invocation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "writer_allowed": False,
    }


__all__ = [
    "ANCHOR_BUDGET_VERIFICATION_CONTEXT_KEYS",
    "BUDGET_V3_IMPLEMENTATION_SHA256",
    "SCHEMA_VERSION",
    "STABILITY_GATE_V2_IMPLEMENTATION_SHA256",
    "STABILITY_GATE_VERIFICATION_CONTEXT_KEYS",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7",
    "verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7",
]
