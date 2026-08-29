from __future__ import annotations

import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_adapter_v5 as adapter_v5,
)
from exchange_terminal.services import (
    strategy_correlation_downside_tail_gate as downside_tail,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = "strategy-correlation-cluster-portfolio-risk-adapter-v6"
STATIC_FINGERPRINT = (
    "20260823-linear-multi-window-downside-tail-joint-risk-lock-1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
ADAPTER_V5_IMPLEMENTATION_SHA256 = (
    "d44d5a1ca180d6b7b432266be6f4ca00cc639ef949a4bc56226ad77d2bccd509"
)
DOWNSIDE_TAIL_IMPLEMENTATION_SHA256 = (
    "9c6f6d0f1f903a384a40cb473e0372a94c124898821b455b0c8eca1863cf33dc"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
TAIL_AGGREGATION_POLICY = (
    "OBSERVED_DOWNSIDE_TAIL_BLOCK_OVERRIDES_ADAPTER_V5_PASS"
)
RISK_REDUCTION_POLICY = (
    "NO_JOINT_EXEMPTION_UNTIL_ADAPTER_V5_TRADE_IDENTITY_FIXTURE_IS_BOUND"
)
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_ADAPTER_CONTEXT_KEYS = {
    "adapter_v4_document",
    "stability_gate_document",
    "adapter_v4_verification_context",
    "stability_gate_verification_context",
}
_TAIL_CONTEXT_KEYS = {
    "expected_registration_hash",
    "expected_evaluation_hash",
}
_AUTHORITY = {
    "research_only": True,
    "local_decision_only": True,
    "risk_service_invocation_allowed": False,
    "formal_registry_activation_allowed": False,
    "current_admission_allowed": False,
    "current_pointer_written": False,
    "migration_allowed": False,
    "runtime_gate_activation_allowed": False,
    "shadow_consumer_activation_allowed": False,
    "writer_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH_RE.fullmatch(value) is not None


def _context_exact(value: Any, keys: set[str]) -> bool:
    return type(value) is dict and set(value) == keys


def _adapter_verification(
    document: Any,
    context: Any,
) -> dict[str, Any]:
    if not _context_exact(context, _ADAPTER_CONTEXT_KEYS):
        return {"status": "BLOCK"}
    try:
        return adapter_v5.verify_strategy_correlation_cluster_portfolio_risk_adapter_v5(
            document,
            context["adapter_v4_document"],
            context["stability_gate_document"],
            adapter_v4_verification_context=context[
                "adapter_v4_verification_context"
            ],
            stability_gate_verification_context=context[
                "stability_gate_verification_context"
            ],
        )
    except (KeyError, MemoryError, TypeError, ValueError):
        return {"status": "BLOCK"}


def _trade_context(adapter_context: Any) -> dict[str, Any] | None:
    if not _context_exact(adapter_context, _ADAPTER_CONTEXT_KEYS):
        return None
    adapter_v4_context = adapter_context.get(
        "adapter_v4_verification_context"
    )
    if type(adapter_v4_context) is not dict:
        return None
    weighted = adapter_v4_context.get(
        "weighted_budget_v2_verification_context"
    )
    if type(weighted) is not dict:
        return None
    positions = weighted.get("positions")
    proposed_symbol = weighted.get("proposed_symbol")
    risk_increasing = weighted.get("risk_increasing")
    if (
        type(positions) is not list
        or type(proposed_symbol) is not str
        or not proposed_symbol
        or type(risk_increasing) is not bool
    ):
        return None
    symbols: list[str] = []
    for item in positions:
        if (
            type(item) is not dict
            or type(item.get("symbol")) is not str
            or not item["symbol"]
        ):
            return None
        symbols.append(item["symbol"])
    symbols.append(proposed_symbol)
    normalized = sorted(set(symbols))
    if not downside_tail.MIN_IDENTITY_COUNT <= len(
        normalized
    ) <= downside_tail.MAX_IDENTITY_COUNT:
        return None
    return {
        "symbols": normalized,
        "symbol_set_hash": strict_canonical_hash(normalized),
        "risk_increasing": risk_increasing,
    }


def _tail_verification(
    registration: Any,
    evaluation: Any,
    context: Any,
) -> tuple[bool, bool]:
    if not _context_exact(context, _TAIL_CONTEXT_KEYS):
        return False, False
    expected_registration_hash = context.get("expected_registration_hash")
    expected_evaluation_hash = context.get("expected_evaluation_hash")
    if not _is_hash(expected_registration_hash) or not _is_hash(
        expected_evaluation_hash
    ):
        return False, False
    try:
        registration_exact = (
            downside_tail.verify_strategy_correlation_downside_tail_registration(
                registration
            )
        )
        evaluation_exact = (
            downside_tail.verify_strategy_correlation_downside_tail_evaluation(
                evaluation,
                registration,
                expected_registration_hash=expected_registration_hash,
                expected_evaluation_hash=expected_evaluation_hash,
            )
        )
    except (KeyError, MemoryError, TypeError, ValueError):
        return False, False
    return registration_exact, evaluation_exact


def _identity_set_bound(
    trade_context: Any,
    registration: Any,
) -> bool:
    return bool(
        type(trade_context) is dict
        and type(registration) is dict
        and type(registration.get("stratum_by_identity")) is dict
        and trade_context.get("symbols")
        == sorted(registration["stratum_by_identity"])
        and trade_context.get("symbol_set_hash")
        == registration.get("identity_set_hash")
        and _is_hash(registration.get("identity_set_hash"))
    )


def _check(name: str, ok: bool) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "blocking": True}


def evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v6(
    adapter_v5_document: Any,
    downside_tail_registration: Any,
    downside_tail_evaluation: Any,
    *,
    adapter_v5_verification_context: Any,
    downside_tail_verification_context: Any,
) -> dict[str, Any]:
    adapter_context_exact = _context_exact(
        adapter_v5_verification_context,
        _ADAPTER_CONTEXT_KEYS,
    )
    adapter_receipt = _adapter_verification(
        adapter_v5_document,
        adapter_v5_verification_context,
    )
    adapter_exact = bool(
        adapter_context_exact
        and adapter_receipt.get("status") == "PASS"
        and type(adapter_v5_document) is dict
        and adapter_v5_document.get("schema_version")
        == adapter_v5.SCHEMA_VERSION
        and adapter_v5_document.get("static_fingerprint")
        == adapter_v5.STATIC_FINGERPRINT
        and _is_hash(adapter_v5_document.get("adapter_v5_hash"))
        and strict_json_contract_equal(
            adapter_v5_document.get("authority"),
            _AUTHORITY,
        )
    )
    trade_context = (
        _trade_context(adapter_v5_verification_context)
        if adapter_exact
        else None
    )
    tail_context_exact = _context_exact(
        downside_tail_verification_context,
        _TAIL_CONTEXT_KEYS,
    )
    tail_registration_exact, tail_evaluation_exact = _tail_verification(
        downside_tail_registration,
        downside_tail_evaluation,
        downside_tail_verification_context,
    )
    tail_hashes_bound = bool(
        tail_context_exact
        and tail_registration_exact
        and tail_evaluation_exact
        and downside_tail_registration.get("registration_hash")
        == downside_tail_verification_context.get(
            "expected_registration_hash"
        )
        and downside_tail_evaluation.get("evaluation_hash")
        == downside_tail_verification_context.get("expected_evaluation_hash")
    )
    tail_observed = bool(
        tail_evaluation_exact
        and downside_tail_evaluation.get("source_state") == "OBSERVED"
        and downside_tail_evaluation.get("gate_decision") in {"PASS", "BLOCK"}
    )
    identity_set_bound = _identity_set_bound(
        trade_context,
        downside_tail_registration,
    )
    risk_direction_exact = bool(
        type(trade_context) is dict
        and type(trade_context.get("risk_increasing")) is bool
    )
    checks = [
        _check("adapter_v5_context_exact", adapter_context_exact),
        _check("adapter_v5_exact_public_verification", adapter_exact),
        _check("downside_tail_context_exact", tail_context_exact),
        _check(
            "downside_tail_registration_exact",
            tail_registration_exact,
        ),
        _check("downside_tail_evaluation_exact", tail_evaluation_exact),
        _check("downside_tail_hashes_cross_bound", tail_hashes_bound),
        _check("downside_tail_source_observed", tail_observed),
        _check("trade_symbol_set_to_tail_identity_set_bound", identity_set_bound),
        _check("risk_direction_strictly_derived", risk_direction_exact),
    ]
    source_known = all(check["ok"] for check in checks)
    adapter_status = (
        adapter_v5_document.get("status")
        if adapter_exact
        else "UNKNOWN"
    )
    tail_decision = (
        downside_tail_evaluation.get("gate_decision")
        if tail_observed
        else "UNKNOWN"
    )
    risk_increasing = (
        trade_context["risk_increasing"] if risk_direction_exact else None
    )

    if not source_known:
        status = "BLOCK"
        decision = "BLOCK_JOINT_SOURCE_UNVERIFIED"
        blockers = [
            check["name"] for check in checks if check["ok"] is not True
        ]
    elif adapter_status == "BLOCK":
        status = "BLOCK"
        decision = "BLOCK_ADAPTER_V5_COMPONENT"
        blockers = ["adapter_v5_component_block"]
    elif adapter_status != "PASS":
        status = "BLOCK"
        decision = "BLOCK_ADAPTER_V5_STATUS_UNKNOWN"
        blockers = ["adapter_v5_status_unknown"]
    elif tail_decision == "BLOCK":
        status = "BLOCK"
        decision = "BLOCK_DOWNSIDE_TAIL_COUPLING"
        blockers = ["downside_tail_coupling_detected"]
    elif tail_decision == "PASS":
        status = "PASS"
        decision = (
            "PASS_LINEAR_MULTI_WINDOW_AND_DOWNSIDE_TAIL_RESEARCH_GATE"
        )
        blockers = []
    else:
        status = "BLOCK"
        decision = "BLOCK_DOWNSIDE_TAIL_STATUS_UNKNOWN"
        blockers = ["downside_tail_status_unknown"]

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": decision,
        "source": {
            "adapter_v5_schema_version": (
                adapter_v5_document.get("schema_version")
                if adapter_exact
                else "UNKNOWN"
            ),
            "adapter_v5_static_fingerprint": (
                adapter_v5_document.get("static_fingerprint")
                if adapter_exact
                else "UNKNOWN"
            ),
            "adapter_v5_hash": (
                adapter_v5_document.get("adapter_v5_hash")
                if adapter_exact
                else None
            ),
            "adapter_v5_implementation_sha256": (
                ADAPTER_V5_IMPLEMENTATION_SHA256
            ),
            "downside_tail_registration_schema_version": (
                downside_tail.REGISTRATION_SCHEMA
            ),
            "downside_tail_registration_hash": (
                downside_tail_registration.get("registration_hash")
                if tail_registration_exact
                else None
            ),
            "downside_tail_evaluation_schema_version": (
                downside_tail.EVALUATION_SCHEMA
            ),
            "downside_tail_evaluation_hash": (
                downside_tail_evaluation.get("evaluation_hash")
                if tail_evaluation_exact
                else None
            ),
            "downside_tail_implementation_sha256": (
                DOWNSIDE_TAIL_IMPLEMENTATION_SHA256
            ),
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
            "trade_identity_hash": (
                adapter_v5_document.get("source", {}).get(
                    "trade_identity_hash"
                )
                if adapter_exact
                else None
            ),
            "trade_symbol_set_hash": (
                trade_context.get("symbol_set_hash")
                if type(trade_context) is dict
                else None
            ),
            "tail_identity_set_hash": (
                downside_tail_registration.get("identity_set_hash")
                if tail_registration_exact
                else None
            ),
            "source_documents_embedded": False,
            "verification_contexts_embedded": False,
        },
        "component_states": {
            "adapter_v5_status": adapter_status,
            "downside_tail_source_state": (
                downside_tail_evaluation.get("source_state")
                if tail_evaluation_exact
                else "UNKNOWN"
            ),
            "downside_tail_gate_decision": tail_decision,
            "downside_tail_gate_reason": (
                downside_tail_evaluation.get("gate_reason")
                if tail_evaluation_exact
                else "UNKNOWN"
            ),
            "risk_increasing": risk_increasing,
        },
        "policy": {
            "tail_aggregation": TAIL_AGGREGATION_POLICY,
            "risk_reduction": RISK_REDUCTION_POLICY,
            "tail_block_overrides_adapter_v5_pass": True,
            "risk_reduction_joint_exemption_implemented": False,
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "adapter_v5_exactly_verified": adapter_exact,
            "downside_tail_registration_exactly_verified": (
                tail_registration_exact
            ),
            "downside_tail_evaluation_exactly_verified": (
                tail_evaluation_exact
            ),
            "trade_symbol_set_tail_identity_set_cross_bound": (
                identity_set_bound
            ),
            "linear_and_multi_window_pass_can_be_overridden_by_tail_block": (
                True
            ),
            "risk_reduction_joint_exemption_implemented": False,
            "joint_local_research_decision_made": source_known,
            "source_documents_embedded": False,
            "verification_contexts_embedded": False,
            "aligned_observations_embedded": False,
            "pair_results_embedded": False,
            "positions_embedded": False,
            "runtime_assets_accessed": False,
            "risk_service_invoked": False,
            "runtime_consumer_bound": False,
            "profitability_proven": False,
        },
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(document, "adapter_v6_hash")


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v6(
    document: Any,
    adapter_v5_document: Any,
    downside_tail_registration: Any,
    downside_tail_evaluation: Any,
    *,
    adapter_v5_verification_context: Any,
    downside_tail_verification_context: Any,
) -> dict[str, Any]:
    expected = evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v6(
        adapter_v5_document,
        downside_tail_registration,
        downside_tail_evaluation,
        adapter_v5_verification_context=adapter_v5_verification_context,
        downside_tail_verification_context=downside_tail_verification_context,
    )
    exact = type(document) is dict and strict_json_contract_equal(
        document,
        expected,
    )
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "adapter_v6_exactly_rebuilt": exact,
        "adapter_v6_status": expected.get("status") if exact else "UNKNOWN",
        "adapter_v6_hash": expected.get("adapter_v6_hash") if exact else None,
        "blockers": [] if exact else ["adapter_v6_exact_rebuild"],
        "risk_reduction_joint_exemption_verified": False,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
    }


__all__ = [
    "ADAPTER_V5_IMPLEMENTATION_SHA256",
    "DOWNSIDE_TAIL_IMPLEMENTATION_SHA256",
    "RISK_REDUCTION_POLICY",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "TAIL_AGGREGATION_POLICY",
    "VERIFICATION_SCHEMA_VERSION",
    "evaluate_strategy_correlation_cluster_portfolio_risk_adapter_v6",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v6",
]
