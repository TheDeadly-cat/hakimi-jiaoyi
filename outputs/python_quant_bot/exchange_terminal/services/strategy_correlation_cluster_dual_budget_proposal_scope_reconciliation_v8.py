from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .strategy_correlation_cluster_effective_bet_budget_v11 import (
    BUDGET_SCHEMA_VERSION as LEGACY_BUDGET_V11_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_effective_bet_budget_v11,
)
from .strategy_correlation_cluster_multi_window_cutoff_bound_effective_ticket_budget_consumer_v7 import (
    CONSUMER_SCHEMA_VERSION as DYNAMIC_BUDGET_V7_SCHEMA_VERSION,
    verify_cutoff_bound_effective_ticket_budget_consumer_v7,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-dual-budget-proposal-scope-"
    "preregistration-v8"
)
RECONCILIATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-dual-budget-proposal-scope-"
    "reconciliation-v8"
)
VERIFICATION_SCHEMA_VERSION = f"{RECONCILIATION_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-correlation-cluster-dual-budget-proposal-scope-v8-lock-1"
)
MAX_INTEGER = 9_999_999_999_999_999

_V7_CONTEXT_KEYS = frozenset(
    {
        "budget_preregistration",
        "common_cutoff_gate_v6_document",
        "common_cutoff_gate_v6_context",
        "positions_before",
        "proposal",
        "equity_minor",
        "expected_budget_preregistration_v7_hash",
    }
)
_V11_CONTEXT_KEYS = frozenset(
    {
        "args",
        "kwargs",
        "expected_budget_v11_hash",
    }
)


class DualBudgetProposalScopeContractError(ValueError):
    pass


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _native_int(
    value: Any,
    field: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise DualBudgetProposalScopeContractError(f"{field}_invalid")
    return value


def _symbol(value: Any) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip().upper()
        or any(character.isspace() for character in value)
    ):
        raise DualBudgetProposalScopeContractError("proposal_symbol_invalid")
    return value


def _direction(value: Any) -> str:
    if value not in {"LONG", "SHORT"}:
        raise DualBudgetProposalScopeContractError("proposal_direction_invalid")
    return value


def _legacy_percent_to_bps(value: Any) -> int | None:
    if type(value) not in {int, float}:
        return None
    try:
        bps = Decimal(str(value)) * Decimal(100)
    except (InvalidOperation, ValueError):
        return None
    if not bps.is_finite() or bps != bps.to_integral_value():
        return None
    result = int(bps)
    return result if 1 <= result <= 10_000 else None


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "consumer_only": True,
        "writer_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "formal_registry_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _check(name: str, ok: bool, passed: str, failed: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": bool(ok),
        "blocking": True,
        "detail": passed if ok else failed,
    }


def build_dual_budget_proposal_scope_preregistration_v8(
    *,
    expected_dynamic_budget_preregistration_v7_hash: Any,
    expected_proposal_symbol: Any,
    expected_proposal_direction: Any,
    expected_proposal_notional_minor: Any,
    expected_max_cluster_gross_bps: Any,
    legacy_notional_unit_to_minor: Any,
    require_legacy_risk_increasing: Any,
) -> dict[str, Any]:
    if not strict_sha256(expected_dynamic_budget_preregistration_v7_hash):
        raise DualBudgetProposalScopeContractError(
            "expected_dynamic_budget_preregistration_v7_hash_invalid"
        )
    symbol = _symbol(expected_proposal_symbol)
    direction = _direction(expected_proposal_direction)
    notional_minor = _native_int(
        expected_proposal_notional_minor,
        "expected_proposal_notional_minor",
        minimum=1,
        maximum=MAX_INTEGER,
    )
    gross_bps = _native_int(
        expected_max_cluster_gross_bps,
        "expected_max_cluster_gross_bps",
        minimum=1,
        maximum=10_000,
    )
    scale = _native_int(
        legacy_notional_unit_to_minor,
        "legacy_notional_unit_to_minor",
        minimum=1,
        maximum=1_000_000,
    )
    if require_legacy_risk_increasing is not True:
        raise DualBudgetProposalScopeContractError(
            "require_legacy_risk_increasing_invalid"
        )
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_RESEARCH_ONLY",
        "source": {
            "dynamic_budget_preregistration_v7_hash": (
                expected_dynamic_budget_preregistration_v7_hash
            ),
        },
        "expected_proposal": {
            "symbol": symbol,
            "direction": direction,
            "notional_minor": notional_minor,
            "max_cluster_gross_bps": gross_bps,
            "legacy_notional_unit_to_minor": scale,
            "legacy_risk_increasing": True,
        },
        "facts": {
            "proposal_scope_defined": True,
            "unit_conversion_defined": True,
            "portfolio_snapshot_hash_required": False,
            "portfolio_snapshot_reconciled": False,
            "dual_budget_combined_admission_allowed": False,
            "runtime_consumer_bound": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        document,
        "proposal_scope_preregistration_v8_hash",
    )


def verify_dual_budget_proposal_scope_preregistration_v8(
    document: Any,
    *,
    expected_proposal_scope_preregistration_v8_hash: Any,
) -> dict[str, Any]:
    exact = False
    if (
        type(document) is dict
        and strict_sha256(expected_proposal_scope_preregistration_v8_hash)
        and document.get("proposal_scope_preregistration_v8_hash")
        == expected_proposal_scope_preregistration_v8_hash
    ):
        try:
            source = _dict(document.get("source"))
            proposal = _dict(document.get("expected_proposal"))
            rebuilt = build_dual_budget_proposal_scope_preregistration_v8(
                expected_dynamic_budget_preregistration_v7_hash=source.get(
                    "dynamic_budget_preregistration_v7_hash"
                ),
                expected_proposal_symbol=proposal.get("symbol"),
                expected_proposal_direction=proposal.get("direction"),
                expected_proposal_notional_minor=proposal.get("notional_minor"),
                expected_max_cluster_gross_bps=proposal.get(
                    "max_cluster_gross_bps"
                ),
                legacy_notional_unit_to_minor=proposal.get(
                    "legacy_notional_unit_to_minor"
                ),
                require_legacy_risk_increasing=proposal.get(
                    "legacy_risk_increasing"
                ),
            )
            exact = strict_json_contract_equal(document, rebuilt)
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ):
            exact = False
    return {
        "schema_version": f"{PREREGISTRATION_SCHEMA_VERSION}-verification-v1",
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["proposal_scope_preregistration_v8_mismatch"],
        "preregistration_exactly_verified": exact,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_dynamic_budget_v7(document: Any, context: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != DYNAMIC_BUDGET_V7_SCHEMA_VERSION
        or type(context) is not dict
        or set(context) != _V7_CONTEXT_KEYS
    ):
        return False
    try:
        verification = verify_cutoff_bound_effective_ticket_budget_consumer_v7(
            document,
            context["budget_preregistration"],
            context["common_cutoff_gate_v6_document"],
            context["common_cutoff_gate_v6_context"],
            context["positions_before"],
            context["proposal"],
            equity_minor=context["equity_minor"],
            expected_budget_preregistration_v7_hash=context[
                "expected_budget_preregistration_v7_hash"
            ],
        )
    except (
        ArithmeticError,
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        return False
    return bool(
        type(verification) is dict
        and verification.get("status") == "PASS"
        and verification.get("consumer_exactly_verified") is True
        and not _list(verification.get("blockers"))
    )


def _verify_legacy_budget_v11(document: Any, context: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version") != LEGACY_BUDGET_V11_SCHEMA_VERSION
        or type(context) is not dict
        or set(context) != _V11_CONTEXT_KEYS
        or type(context.get("args")) is not list
        or type(context.get("kwargs")) is not dict
        or not strict_sha256(context.get("expected_budget_v11_hash"))
        or document.get("budget_v11_hash") != context.get("expected_budget_v11_hash")
    ):
        return False
    try:
        return bool(
            verify_strategy_correlation_cluster_effective_bet_budget_v11(
                document,
                *context["args"],
                expected_budget_v11_hash=context["expected_budget_v11_hash"],
                **context["kwargs"],
            )
        )
    except Exception:
        return False


def evaluate_dual_budget_proposal_scope_reconciliation_v8(
    preregistration: Any,
    dynamic_budget_v7_document: Any,
    dynamic_budget_v7_context: Any,
    legacy_budget_v11_document: Any,
    legacy_budget_v11_context: Any,
    *,
    expected_proposal_scope_preregistration_v8_hash: Any,
) -> dict[str, Any]:
    preregistration_verification = (
        verify_dual_budget_proposal_scope_preregistration_v8(
            preregistration,
            expected_proposal_scope_preregistration_v8_hash=(
                expected_proposal_scope_preregistration_v8_hash
            ),
        )
    )
    preregistration_ok = preregistration_verification.get("status") == "PASS"
    dynamic_exact = _verify_dynamic_budget_v7(
        dynamic_budget_v7_document,
        dynamic_budget_v7_context,
    )
    legacy_exact = _verify_legacy_budget_v11(
        legacy_budget_v11_document,
        legacy_budget_v11_context,
    )

    expected = _dict(_dict(preregistration).get("expected_proposal"))
    source = _dict(_dict(preregistration).get("source"))
    dynamic_context = _dict(dynamic_budget_v7_context)
    dynamic_preregistration = _dict(dynamic_context.get("budget_preregistration"))
    dynamic_policy = _dict(dynamic_preregistration.get("policy"))
    dynamic_proposal = _dict(dynamic_context.get("proposal"))
    legacy_kwargs = _dict(_dict(legacy_budget_v11_context).get("kwargs"))

    predecessor_hash_binding_ok = bool(
        preregistration_ok
        and dynamic_exact
        and dynamic_preregistration.get("budget_preregistration_v7_hash")
        == source.get("dynamic_budget_preregistration_v7_hash")
        == dynamic_context.get("expected_budget_preregistration_v7_hash")
    )
    dynamic_local_pass = bool(
        dynamic_exact
        and _dict(dynamic_budget_v7_document).get("status") == "PASS"
        and _dict(dynamic_budget_v7_document).get("budget_status") == "PASS"
        and _dict(dynamic_budget_v7_document).get("admission_status") == "BLOCKED"
    )
    legacy_local_pass = bool(
        legacy_exact
        and _dict(legacy_budget_v11_document).get("status") == "PASS"
        and _dict(legacy_budget_v11_document).get("admission_status") == "BLOCKED"
    )
    expected_scale = expected.get("legacy_notional_unit_to_minor")
    legacy_notional = legacy_kwargs.get("proposed_notional")
    converted_legacy_notional = None
    if type(expected_scale) is int and type(legacy_notional) is int:
        converted_legacy_notional = legacy_notional * expected_scale

    symbol_ok = bool(
        preregistration_ok
        and dynamic_exact
        and legacy_exact
        and dynamic_proposal.get("symbol")
        == legacy_kwargs.get("proposed_symbol")
        == expected.get("symbol")
    )
    direction_ok = bool(
        preregistration_ok
        and dynamic_exact
        and legacy_exact
        and dynamic_proposal.get("direction")
        == legacy_kwargs.get("proposed_direction")
        == expected.get("direction")
    )
    notional_ok = bool(
        preregistration_ok
        and dynamic_exact
        and legacy_exact
        and type(legacy_notional) is int
        and converted_legacy_notional == dynamic_proposal.get("notional_minor")
        == expected.get("notional_minor")
    )
    legacy_gross_bps = _legacy_percent_to_bps(
        legacy_kwargs.get("max_cluster_gross_pct")
    )
    gross_limit_ok = bool(
        preregistration_ok
        and dynamic_exact
        and legacy_exact
        and dynamic_policy.get("max_cluster_gross_bps")
        == legacy_gross_bps
        == expected.get("max_cluster_gross_bps")
    )
    risk_increasing_ok = bool(
        preregistration_ok
        and legacy_exact
        and legacy_kwargs.get("risk_increasing") is True
        and expected.get("legacy_risk_increasing") is True
        and dynamic_policy.get("proposal_action") == "ADD_GROSS_EXPOSURE"
    )
    predecessor_authority_locked = bool(
        dynamic_exact
        and legacy_exact
        and _dict(dynamic_budget_v7_document).get("admission_status") == "BLOCKED"
        and _dict(legacy_budget_v11_document).get("admission_status") == "BLOCKED"
        and _dict(_dict(dynamic_budget_v7_document).get("authority")).get(
            "current_admission_allowed"
        )
        is False
        and _dict(_dict(legacy_budget_v11_document).get("authority")).get(
            "current_admission_allowed"
        )
        is False
    )

    checks = [
        _check(
            "proposal_scope_preregistration_v8_exact",
            preregistration_ok,
            "Proposal-scope preregistration exactly verifies.",
            "Proposal-scope preregistration is invalid or mismatched.",
        ),
        _check(
            "dynamic_budget_v7_exact",
            dynamic_exact,
            "Dynamic cutoff-bound budget v7 exactly verifies.",
            "Dynamic cutoff-bound budget v7 is invalid or mismatched.",
        ),
        _check(
            "legacy_budget_v11_exact",
            legacy_exact,
            "Legacy effective-bet budget v11 exactly verifies.",
            "Legacy effective-bet budget v11 is invalid or mismatched.",
        ),
        _check(
            "dynamic_budget_v7_local_pass",
            dynamic_local_pass,
            "Dynamic budget local condition is PASS with admission blocked.",
            "Dynamic budget local condition is not PASS.",
        ),
        _check(
            "legacy_budget_v11_local_pass",
            legacy_local_pass,
            "Legacy budget local condition is PASS with admission blocked.",
            "Legacy budget local condition is not PASS.",
        ),
        _check(
            "dynamic_preregistration_hash_binding",
            predecessor_hash_binding_ok,
            "Dynamic budget preregistration hash matches proposal scope.",
            "Dynamic budget preregistration hash differs from proposal scope.",
        ),
        _check(
            "proposal_symbol_exact",
            symbol_ok,
            "Both budgets evaluate the preregistered symbol.",
            "Proposal symbols differ across budgets or preregistration.",
        ),
        _check(
            "proposal_direction_exact",
            direction_ok,
            "Both budgets evaluate the preregistered direction.",
            "Proposal directions differ across budgets or preregistration.",
        ),
        _check(
            "proposal_notional_unit_conversion_exact",
            notional_ok,
            "Legacy notional converts exactly to dynamic minor units.",
            "Proposal notionals differ after preregistered unit conversion.",
        ),
        _check(
            "cluster_gross_limit_exact",
            gross_limit_ok,
            "Legacy percent and dynamic bps limits are exactly equal.",
            "Cluster gross limits differ across budgets or preregistration.",
        ),
        _check(
            "risk_increasing_semantics_exact",
            risk_increasing_ok,
            "Both contracts represent an additive risk-increasing proposal.",
            "Risk-increasing proposal semantics are not exactly aligned.",
        ),
        _check(
            "predecessor_admission_authority_locked",
            predecessor_authority_locked,
            "Both predecessor admission authorities remain blocked.",
            "A predecessor admission or authority lock is invalid.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    exact_sources = preregistration_ok and dynamic_exact and legacy_exact
    scope_exact = bool(
        predecessor_hash_binding_ok
        and symbol_ok
        and direction_ok
        and notional_ok
        and gross_limit_ok
        and risk_increasing_ok
        and predecessor_authority_locked
    )
    if not exact_sources:
        status = "UNKNOWN"
    elif dynamic_local_pass and legacy_local_pass and scope_exact:
        status = "PASS"
    else:
        status = "BLOCK"
    if not preregistration_ok or not dynamic_exact or not legacy_exact:
        first_blocking_tier = "SOURCE"
    elif not dynamic_local_pass or not legacy_local_pass:
        first_blocking_tier = "PREDECESSOR_DECISION"
    elif not predecessor_hash_binding_ok:
        first_blocking_tier = "PREDECESSOR_HASH"
    elif not symbol_ok:
        first_blocking_tier = "PROPOSAL_SYMBOL"
    elif not direction_ok:
        first_blocking_tier = "PROPOSAL_DIRECTION"
    elif not notional_ok:
        first_blocking_tier = "PROPOSAL_NOTIONAL"
    elif not gross_limit_ok:
        first_blocking_tier = "CLUSTER_GROSS_POLICY"
    elif not risk_increasing_ok:
        first_blocking_tier = "RISK_SEMANTICS"
    elif not predecessor_authority_locked:
        first_blocking_tier = "PERMISSION"
    else:
        first_blocking_tier = None

    document = {
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "reconciliation_status": status,
        "combined_budget_status": "NOT_ESTABLISHED",
        "combined_admission_status": "BLOCKED",
        "decision": (
            "PASS_DUAL_BUDGET_PROPOSAL_SCOPE_RECONCILED_"
            "PORTFOLIO_SNAPSHOT_UNBOUND_V8"
            if status == "PASS"
            else (
                "BLOCK_DUAL_BUDGET_PROPOSAL_SCOPE_MISMATCH_V8"
                if status == "BLOCK"
                else "UNKNOWN_DUAL_BUDGET_PROPOSAL_SCOPE_UNVERIFIED_V8"
            )
        ),
        "first_blocking_tier": first_blocking_tier,
        "source": {
            "proposal_scope_preregistration_v8_hash": (
                _dict(preregistration).get(
                    "proposal_scope_preregistration_v8_hash"
                )
                if preregistration_ok
                else None
            ),
            "dynamic_budget_preregistration_v7_hash": (
                source.get("dynamic_budget_preregistration_v7_hash")
                if predecessor_hash_binding_ok
                else None
            ),
            "dynamic_budget_consumer_v7_hash": (
                _dict(dynamic_budget_v7_document).get("budget_consumer_v7_hash")
                if dynamic_exact
                else None
            ),
            "legacy_budget_v11_hash": (
                _dict(legacy_budget_v11_document).get("budget_v11_hash")
                if legacy_exact
                else None
            ),
            "dynamic_proposal_hash": (
                _dict(_dict(dynamic_budget_v7_document).get("source")).get(
                    "proposal_hash"
                )
                if dynamic_exact
                else None
            ),
        },
        "proposal_scope": {
            "symbol": expected.get("symbol") if preregistration_ok else None,
            "direction": expected.get("direction") if preregistration_ok else None,
            "expected_notional_minor": (
                expected.get("notional_minor") if preregistration_ok else None
            ),
            "dynamic_notional_minor": (
                dynamic_proposal.get("notional_minor") if dynamic_exact else None
            ),
            "legacy_notional": legacy_notional if legacy_exact else None,
            "legacy_notional_unit_to_minor": (
                expected_scale if preregistration_ok else None
            ),
            "converted_legacy_notional_minor": (
                converted_legacy_notional if legacy_exact else None
            ),
            "expected_max_cluster_gross_bps": (
                expected.get("max_cluster_gross_bps")
                if preregistration_ok
                else None
            ),
            "dynamic_max_cluster_gross_bps": (
                dynamic_policy.get("max_cluster_gross_bps")
                if dynamic_exact
                else None
            ),
            "legacy_max_cluster_gross_bps": (
                legacy_gross_bps if legacy_exact else None
            ),
            "legacy_risk_increasing": (
                legacy_kwargs.get("risk_increasing") if legacy_exact else None
            ),
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "dynamic_budget_v7_exact": dynamic_exact,
            "legacy_budget_v11_exact": legacy_exact,
            "both_local_budget_conditions_pass": (
                dynamic_local_pass and legacy_local_pass
            ),
            "proposal_scope_reconciled": scope_exact,
            "portfolio_snapshot_hash_available_from_v11": False,
            "portfolio_snapshot_reconciled": False,
            "positions_reconciled": False,
            "equity_reconciled": False,
            "combined_budget_established": False,
            "combined_admission_allowed": False,
            "runtime_consumer_bound": False,
            "execution_verified": False,
            "profitability_proven": False,
            "raw_predecessor_context_embedded": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        document,
        "proposal_scope_reconciliation_v8_hash",
    )


def verify_dual_budget_proposal_scope_reconciliation_v8(
    document: Any,
    preregistration: Any,
    dynamic_budget_v7_document: Any,
    dynamic_budget_v7_context: Any,
    legacy_budget_v11_document: Any,
    legacy_budget_v11_context: Any,
    *,
    expected_proposal_scope_preregistration_v8_hash: Any,
) -> dict[str, Any]:
    expected = evaluate_dual_budget_proposal_scope_reconciliation_v8(
        preregistration,
        dynamic_budget_v7_document,
        dynamic_budget_v7_context,
        legacy_budget_v11_document,
        legacy_budget_v11_context,
        expected_proposal_scope_preregistration_v8_hash=(
            expected_proposal_scope_preregistration_v8_hash
        ),
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["proposal_scope_v8_exact_rebuild_mismatch"],
        "reconciliation_status": expected["status"] if exact else "UNKNOWN",
        "combined_budget_status": "NOT_ESTABLISHED",
        "combined_admission_status": "BLOCKED",
        "reconciliation_exactly_verified": exact,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "DualBudgetProposalScopeContractError",
    "PREREGISTRATION_SCHEMA_VERSION",
    "RECONCILIATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "build_dual_budget_proposal_scope_preregistration_v8",
    "evaluate_dual_budget_proposal_scope_reconciliation_v8",
    "verify_dual_budget_proposal_scope_preregistration_v8",
    "verify_dual_budget_proposal_scope_reconciliation_v8",
]
