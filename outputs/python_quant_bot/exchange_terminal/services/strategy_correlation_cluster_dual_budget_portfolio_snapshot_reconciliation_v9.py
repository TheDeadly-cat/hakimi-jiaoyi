from __future__ import annotations

from decimal import Decimal, InvalidOperation
from inspect import signature
from typing import Any

from .strategy_correlation_cluster_dual_budget_proposal_scope_reconciliation_v8 import (
    RECONCILIATION_SCHEMA_VERSION as PROPOSAL_RECONCILIATION_V8_SCHEMA_VERSION,
    verify_dual_budget_proposal_scope_reconciliation_v8,
)
from .strategy_correlation_cluster_effective_bet_budget_v11 import (
    evaluate_strategy_correlation_cluster_effective_bet_budget_v11,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-dual-budget-portfolio-snapshot-scope-"
    "preregistration-v9"
)
RECONCILIATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-dual-budget-portfolio-snapshot-"
    "reconciliation-v9"
)
VERIFICATION_SCHEMA_VERSION = f"{RECONCILIATION_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-correlation-cluster-dual-budget-portfolio-snapshot-v9-lock-1"
)
SNAPSHOT_POSITION_SEMANTICS = "PRE_PROPOSAL_POSITIONS"
POSITION_RECONCILIATION_RULE = (
    "EXACT_SYMBOL_DIRECTION_NOTIONAL_AFTER_INTEGER_UNIT_SCALE"
)
MAX_INTEGER = 9_999_999_999_999_999

_V8_CONTEXT_KEYS = frozenset(
    {
        "preregistration",
        "dynamic_budget_v7_document",
        "dynamic_budget_v7_context",
        "legacy_budget_v11_document",
        "legacy_budget_v11_context",
        "expected_proposal_scope_preregistration_v8_hash",
    }
)


class DualBudgetPortfolioSnapshotContractError(ValueError):
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
        raise DualBudgetPortfolioSnapshotContractError(f"{field}_invalid")
    return value


def _scaled_int(value: Any, scale: Any) -> int | None:
    if type(scale) is not int or scale <= 0 or type(value) not in {int, float}:
        return None
    try:
        scaled = Decimal(str(value)) * Decimal(scale)
    except (InvalidOperation, ValueError):
        return None
    if not scaled.is_finite() or scaled != scaled.to_integral_value():
        return None
    result = int(scaled)
    return result if 0 <= result <= MAX_INTEGER else None


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


def _normalize_dynamic_positions(
    positions: Any,
) -> list[dict[str, Any]] | None:
    if type(positions) is not list:
        return None
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in positions:
        if type(item) is not dict or set(item) != {
            "symbol",
            "notional_minor",
            "direction",
        }:
            return None
        symbol = item.get("symbol")
        notional = item.get("notional_minor")
        direction = item.get("direction")
        if (
            type(symbol) is not str
            or not symbol
            or symbol != symbol.strip().upper()
            or symbol in seen
            or type(notional) is not int
            or notional <= 0
            or notional > MAX_INTEGER
            or direction not in {"LONG", "SHORT"}
        ):
            return None
        seen.add(symbol)
        normalized.append(
            {
                "symbol": symbol,
                "notional_minor": notional,
                "direction": direction,
            }
        )
    return sorted(normalized, key=lambda item: item["symbol"])


def _normalize_legacy_positions(
    positions: Any,
    scale: Any,
) -> list[dict[str, Any]] | None:
    if type(positions) is not list:
        return None
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in positions:
        if type(item) is not dict or set(item) != {
            "symbol",
            "notional",
            "direction",
        }:
            return None
        symbol = item.get("symbol")
        direction = item.get("direction")
        notional_minor = _scaled_int(item.get("notional"), scale)
        if (
            type(symbol) is not str
            or not symbol
            or symbol != symbol.strip().upper()
            or symbol in seen
            or notional_minor is None
            or notional_minor <= 0
            or direction not in {"LONG", "SHORT"}
        ):
            return None
        seen.add(symbol)
        normalized.append(
            {
                "symbol": symbol,
                "notional_minor": notional_minor,
                "direction": direction,
            }
        )
    return sorted(normalized, key=lambda item: item["symbol"])


def build_dual_budget_portfolio_snapshot_preregistration_v9(
    *,
    expected_proposal_scope_preregistration_v8_hash: Any,
    expected_legacy_snapshot_claim_hash: Any,
    expected_dynamic_positions_before_hash: Any,
    expected_equity_minor: Any,
    expected_snapshot_sequence: Any,
    expected_observed_at_unix_ms: Any,
    legacy_portfolio_unit_to_minor: Any,
    snapshot_position_semantics: Any,
    position_reconciliation_rule: Any,
) -> dict[str, Any]:
    for value, field in (
        (
            expected_proposal_scope_preregistration_v8_hash,
            "expected_proposal_scope_preregistration_v8_hash",
        ),
        (expected_legacy_snapshot_claim_hash, "expected_legacy_snapshot_claim_hash"),
        (
            expected_dynamic_positions_before_hash,
            "expected_dynamic_positions_before_hash",
        ),
    ):
        if not strict_sha256(value):
            raise DualBudgetPortfolioSnapshotContractError(f"{field}_invalid")
    equity = _native_int(
        expected_equity_minor,
        "expected_equity_minor",
        minimum=1,
        maximum=MAX_INTEGER,
    )
    sequence = _native_int(
        expected_snapshot_sequence,
        "expected_snapshot_sequence",
        minimum=0,
        maximum=MAX_INTEGER,
    )
    observed = _native_int(
        expected_observed_at_unix_ms,
        "expected_observed_at_unix_ms",
        minimum=1,
        maximum=MAX_INTEGER,
    )
    scale = _native_int(
        legacy_portfolio_unit_to_minor,
        "legacy_portfolio_unit_to_minor",
        minimum=1,
        maximum=1_000_000,
    )
    if snapshot_position_semantics != SNAPSHOT_POSITION_SEMANTICS:
        raise DualBudgetPortfolioSnapshotContractError(
            "snapshot_position_semantics_invalid"
        )
    if position_reconciliation_rule != POSITION_RECONCILIATION_RULE:
        raise DualBudgetPortfolioSnapshotContractError(
            "position_reconciliation_rule_invalid"
        )
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_RESEARCH_ONLY",
        "source": {
            "proposal_scope_preregistration_v8_hash": (
                expected_proposal_scope_preregistration_v8_hash
            ),
            "legacy_snapshot_claim_hash": expected_legacy_snapshot_claim_hash,
            "dynamic_positions_before_hash": expected_dynamic_positions_before_hash,
        },
        "expected_snapshot": {
            "equity_minor": equity,
            "snapshot_sequence": sequence,
            "observed_at_unix_ms": observed,
            "legacy_portfolio_unit_to_minor": scale,
            "snapshot_position_semantics": SNAPSHOT_POSITION_SEMANTICS,
            "position_reconciliation_rule": POSITION_RECONCILIATION_RULE,
        },
        "facts": {
            "portfolio_snapshot_scope_defined": True,
            "proposal_scope_reconciliation_required": True,
            "external_snapshot_provider_identity_verified": False,
            "snapshot_source_truth_verified": False,
            "snapshot_freshness_verified": False,
            "runtime_consumer_bound": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        document,
        "portfolio_snapshot_preregistration_v9_hash",
    )


def verify_dual_budget_portfolio_snapshot_preregistration_v9(
    document: Any,
    *,
    expected_portfolio_snapshot_preregistration_v9_hash: Any,
) -> dict[str, Any]:
    exact = False
    if (
        type(document) is dict
        and strict_sha256(expected_portfolio_snapshot_preregistration_v9_hash)
        and document.get("portfolio_snapshot_preregistration_v9_hash")
        == expected_portfolio_snapshot_preregistration_v9_hash
    ):
        try:
            source = _dict(document.get("source"))
            expected = _dict(document.get("expected_snapshot"))
            rebuilt = build_dual_budget_portfolio_snapshot_preregistration_v9(
                expected_proposal_scope_preregistration_v8_hash=source.get(
                    "proposal_scope_preregistration_v8_hash"
                ),
                expected_legacy_snapshot_claim_hash=source.get(
                    "legacy_snapshot_claim_hash"
                ),
                expected_dynamic_positions_before_hash=source.get(
                    "dynamic_positions_before_hash"
                ),
                expected_equity_minor=expected.get("equity_minor"),
                expected_snapshot_sequence=expected.get("snapshot_sequence"),
                expected_observed_at_unix_ms=expected.get(
                    "observed_at_unix_ms"
                ),
                legacy_portfolio_unit_to_minor=expected.get(
                    "legacy_portfolio_unit_to_minor"
                ),
                snapshot_position_semantics=expected.get(
                    "snapshot_position_semantics"
                ),
                position_reconciliation_rule=expected.get(
                    "position_reconciliation_rule"
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
        "blockers": [] if exact else ["portfolio_snapshot_preregistration_v9_mismatch"],
        "preregistration_exactly_verified": exact,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _verify_proposal_reconciliation_v8(document: Any, context: Any) -> bool:
    if (
        type(document) is not dict
        or document.get("schema_version")
        != PROPOSAL_RECONCILIATION_V8_SCHEMA_VERSION
        or type(context) is not dict
        or set(context) != _V8_CONTEXT_KEYS
    ):
        return False
    try:
        verification = verify_dual_budget_proposal_scope_reconciliation_v8(
            document,
            context["preregistration"],
            context["dynamic_budget_v7_document"],
            context["dynamic_budget_v7_context"],
            context["legacy_budget_v11_document"],
            context["legacy_budget_v11_context"],
            expected_proposal_scope_preregistration_v8_hash=context[
                "expected_proposal_scope_preregistration_v8_hash"
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
        and verification.get("reconciliation_exactly_verified") is True
        and not _list(verification.get("blockers"))
    )


def _bind_legacy_v11_context(v11_context: Any) -> dict[str, Any]:
    context = _dict(v11_context)
    args = context.get("args")
    kwargs = context.get("kwargs")
    if type(args) is not list or type(kwargs) is not dict:
        return {}
    try:
        return dict(
            signature(
                evaluate_strategy_correlation_cluster_effective_bet_budget_v11
            ).bind(*args, **kwargs).arguments
        )
    except (TypeError, ValueError):
        return {}


def evaluate_dual_budget_portfolio_snapshot_reconciliation_v9(
    preregistration: Any,
    proposal_reconciliation_v8_document: Any,
    proposal_reconciliation_v8_context: Any,
    *,
    expected_portfolio_snapshot_preregistration_v9_hash: Any,
) -> dict[str, Any]:
    preregistration_verification = (
        verify_dual_budget_portfolio_snapshot_preregistration_v9(
            preregistration,
            expected_portfolio_snapshot_preregistration_v9_hash=(
                expected_portfolio_snapshot_preregistration_v9_hash
            ),
        )
    )
    preregistration_ok = preregistration_verification.get("status") == "PASS"
    proposal_reconciliation_exact = _verify_proposal_reconciliation_v8(
        proposal_reconciliation_v8_document,
        proposal_reconciliation_v8_context,
    )
    proposal_reconciliation_pass = bool(
        proposal_reconciliation_exact
        and _dict(proposal_reconciliation_v8_document).get("status") == "PASS"
        and _dict(proposal_reconciliation_v8_document).get(
            "combined_admission_status"
        )
        == "BLOCKED"
    )

    preregistration_document = _dict(preregistration)
    preregistration_source = _dict(preregistration_document.get("source"))
    expected = _dict(preregistration_document.get("expected_snapshot"))
    v8_context = _dict(proposal_reconciliation_v8_context)
    v8_preregistration = _dict(v8_context.get("preregistration"))
    dynamic_v7_document = _dict(v8_context.get("dynamic_budget_v7_document"))
    dynamic_v7_context = _dict(v8_context.get("dynamic_budget_v7_context"))
    legacy_v11_document = _dict(v8_context.get("legacy_budget_v11_document"))
    legacy_v11_context = _dict(v8_context.get("legacy_budget_v11_context"))
    legacy_bound = _bind_legacy_v11_context(legacy_v11_context)

    predecessor_hash_ok = bool(
        preregistration_ok
        and proposal_reconciliation_exact
        and v8_preregistration.get("proposal_scope_preregistration_v8_hash")
        == preregistration_source.get("proposal_scope_preregistration_v8_hash")
        == v8_context.get("expected_proposal_scope_preregistration_v8_hash")
    )
    snapshot_claim = _dict(legacy_bound.get("snapshot_claim_document"))
    snapshot = _dict(snapshot_claim.get("snapshot"))
    snapshot_evidence = _dict(legacy_bound.get("snapshot_evidence_document"))
    snapshot_evidence_source = _dict(snapshot_evidence.get("source"))
    snapshot_evidence_summary = _dict(snapshot_evidence.get("snapshot_summary"))
    transition = _dict(legacy_bound.get("transition_document"))
    transition_source = _dict(transition.get("source"))
    snapshot_kwargs = _dict(legacy_bound.get("snapshot_evaluation_kwargs"))
    claim_build_kwargs = _dict(snapshot_kwargs.get("claim_build_kwargs"))
    legacy_summary = _dict(legacy_v11_document.get("snapshot_summary"))

    snapshot_lineage_ok = bool(
        proposal_reconciliation_exact
        and snapshot_claim.get("snapshot_claim_hash")
        == preregistration_source.get("legacy_snapshot_claim_hash")
        and strict_sha256(snapshot_claim.get("snapshot_claim_hash"))
        and snapshot_evidence.get("status") == "PASS"
        and snapshot_evidence_source.get("snapshot_claim_hash")
        == snapshot_claim.get("snapshot_claim_hash")
        and strict_sha256(snapshot_evidence.get("snapshot_evidence_hash"))
        and transition.get("status") == "PASS"
        and transition_source.get("snapshot_evidence_hash")
        == snapshot_evidence.get("snapshot_evidence_hash")
        and claim_build_kwargs.get("snapshot_id_hash")
        == snapshot.get("snapshot_id_hash")
        and claim_build_kwargs.get("snapshot_sequence")
        == snapshot.get("snapshot_sequence")
        and claim_build_kwargs.get("observed_at_unix_ms")
        == snapshot.get("observed_at_unix_ms")
        and snapshot_evidence_summary.get("snapshot_sequence")
        == snapshot.get("snapshot_sequence")
        and snapshot_evidence_summary.get("observed_at_unix_ms")
        == snapshot.get("observed_at_unix_ms")
        and legacy_summary.get("snapshot_id_hash")
        == snapshot.get("snapshot_id_hash")
        and legacy_summary.get("snapshot_sequence")
        == snapshot.get("snapshot_sequence")
        and legacy_summary.get("observed_at_unix_ms")
        == snapshot.get("observed_at_unix_ms")
    )

    scale = expected.get("legacy_portfolio_unit_to_minor")
    dynamic_positions = _normalize_dynamic_positions(
        dynamic_v7_context.get("positions_before")
    )
    legacy_positions = _normalize_legacy_positions(snapshot.get("positions"), scale)
    legacy_build_positions = _normalize_legacy_positions(
        claim_build_kwargs.get("positions"),
        scale,
    )
    dynamic_positions_hash = (
        strict_canonical_hash(dynamic_positions)
        if dynamic_positions is not None
        else None
    )
    legacy_positions_hash = (
        strict_canonical_hash(legacy_positions)
        if legacy_positions is not None
        else None
    )
    position_scope_ok = bool(
        proposal_reconciliation_exact
        and dynamic_positions is not None
        and legacy_positions is not None
        and legacy_build_positions == legacy_positions
        and dynamic_positions == legacy_positions
        and dynamic_positions_hash == legacy_positions_hash
        == preregistration_source.get("dynamic_positions_before_hash")
        == _dict(dynamic_v7_document.get("source")).get("positions_before_hash")
    )

    dynamic_equity = dynamic_v7_context.get("equity_minor")
    legacy_equity = _scaled_int(snapshot.get("equity"), scale)
    legacy_build_equity = _scaled_int(claim_build_kwargs.get("equity"), scale)
    equity_scope_ok = bool(
        proposal_reconciliation_exact
        and type(dynamic_equity) is int
        and dynamic_equity > 0
        and dynamic_equity == legacy_equity == legacy_build_equity
        == expected.get("equity_minor")
    )
    legacy_gross_minor = _scaled_int(
        snapshot.get("portfolio_gross_notional"),
        scale,
    )
    normalized_gross_minor = (
        sum(item["notional_minor"] for item in legacy_positions)
        if legacy_positions is not None
        else None
    )
    summary_scope_ok = bool(
        snapshot_lineage_ok
        and legacy_gross_minor == normalized_gross_minor
        and snapshot.get("position_count")
        == len(legacy_positions or [])
        and snapshot_evidence_summary.get("position_count")
        == snapshot.get("position_count")
        and _scaled_int(snapshot_evidence_summary.get("equity"), scale)
        == legacy_equity
        and _scaled_int(
            snapshot_evidence_summary.get("portfolio_gross_notional"),
            scale,
        )
        == legacy_gross_minor
        and _scaled_int(legacy_summary.get("equity"), scale) == legacy_equity
        and _scaled_int(
            legacy_summary.get("portfolio_gross_notional"),
            scale,
        )
        == legacy_gross_minor
        and legacy_summary.get("position_count")
        == snapshot.get("position_count")
    )
    sequence_scope_ok = bool(
        snapshot_lineage_ok
        and snapshot.get("snapshot_sequence")
        == expected.get("snapshot_sequence")
        and snapshot.get("observed_at_unix_ms")
        == expected.get("observed_at_unix_ms")
    )
    snapshot_facts = _dict(snapshot_evidence.get("facts"))
    source_truth_locked = bool(
        snapshot_lineage_ok
        and snapshot_facts.get("provider_identity_verified") is False
        and snapshot_facts.get("provider_implementation_verified") is False
        and snapshot_facts.get("snapshot_source_truth_verified") is False
        and snapshot_facts.get("snapshot_freshness_verified") is False
        and _dict(snapshot_evidence.get("authority")).get(
            "current_admission_allowed"
        )
        is False
    )

    checks = [
        _check(
            "portfolio_snapshot_preregistration_v9_exact",
            preregistration_ok,
            "Portfolio snapshot preregistration exactly verifies.",
            "Portfolio snapshot preregistration is invalid or mismatched.",
        ),
        _check(
            "proposal_reconciliation_v8_exact",
            proposal_reconciliation_exact,
            "Proposal reconciliation v8 exactly verifies.",
            "Proposal reconciliation v8 is invalid or mismatched.",
        ),
        _check(
            "proposal_reconciliation_v8_pass",
            proposal_reconciliation_pass,
            "Proposal reconciliation v8 is locally PASS with admission blocked.",
            "Proposal reconciliation v8 is not locally PASS.",
        ),
        _check(
            "proposal_preregistration_hash_binding",
            predecessor_hash_ok,
            "Portfolio scope binds the exact proposal preregistration hash.",
            "Proposal preregistration hash differs from portfolio scope.",
        ),
        _check(
            "legacy_snapshot_lineage_exact",
            snapshot_lineage_ok,
            "Snapshot claim, evidence, transition, and v11 summary align.",
            "Legacy snapshot lineage is incomplete or mismatched.",
        ),
        _check(
            "pre_proposal_positions_exact",
            position_scope_ok,
            "Dynamic and legacy pre-proposal positions exactly match.",
            "Pre-proposal positions differ after integer unit conversion.",
        ),
        _check(
            "portfolio_equity_exact",
            equity_scope_ok,
            "Dynamic and legacy equity exactly match.",
            "Portfolio equity differs after integer unit conversion.",
        ),
        _check(
            "snapshot_summary_arithmetic_exact",
            summary_scope_ok,
            "Position count, gross, and equity summaries exactly recompute.",
            "Snapshot summary count, gross, or equity is inconsistent.",
        ),
        _check(
            "snapshot_sequence_and_observed_time_exact",
            sequence_scope_ok,
            "Snapshot sequence and observed time match preregistration.",
            "Snapshot sequence or observed time differs from preregistration.",
        ),
        _check(
            "snapshot_external_authority_remains_locked",
            source_truth_locked,
            "External snapshot source truth and admission remain locked.",
            "Snapshot source-truth or authority limitations are inconsistent.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    exact_sources = preregistration_ok and proposal_reconciliation_exact
    portfolio_scope_exact = bool(
        proposal_reconciliation_pass
        and predecessor_hash_ok
        and snapshot_lineage_ok
        and position_scope_ok
        and equity_scope_ok
        and summary_scope_ok
        and sequence_scope_ok
        and source_truth_locked
    )
    if not exact_sources:
        status = "UNKNOWN"
    elif portfolio_scope_exact:
        status = "PASS"
    else:
        status = "BLOCK"
    if not preregistration_ok or not proposal_reconciliation_exact:
        first_blocking_tier = "SOURCE"
    elif not proposal_reconciliation_pass:
        first_blocking_tier = "PROPOSAL_SCOPE"
    elif not predecessor_hash_ok:
        first_blocking_tier = "PREDECESSOR_HASH"
    elif not snapshot_lineage_ok:
        first_blocking_tier = "SNAPSHOT_LINEAGE"
    elif not position_scope_ok:
        first_blocking_tier = "POSITIONS"
    elif not equity_scope_ok:
        first_blocking_tier = "EQUITY"
    elif not summary_scope_ok:
        first_blocking_tier = "SNAPSHOT_SUMMARY"
    elif not sequence_scope_ok:
        first_blocking_tier = "SNAPSHOT_SEQUENCE"
    elif not source_truth_locked:
        first_blocking_tier = "PERMISSION"
    else:
        first_blocking_tier = None

    document = {
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "portfolio_scope_status": status,
        "combined_budget_scope_status": (
            "PASS" if status == "PASS" else "NOT_ESTABLISHED"
        ),
        "combined_budget_status": (
            "LOCAL_RESEARCH_SCOPE_RECONCILED"
            if status == "PASS"
            else "NOT_ESTABLISHED"
        ),
        "combined_admission_status": "BLOCKED",
        "decision": (
            "PASS_DUAL_BUDGET_PROPOSAL_AND_PORTFOLIO_SCOPE_RECONCILED_"
            "EXTERNAL_SNAPSHOT_TRUTH_UNVERIFIED_V9"
            if status == "PASS"
            else (
                "BLOCK_DUAL_BUDGET_PORTFOLIO_SCOPE_MISMATCH_V9"
                if status == "BLOCK"
                else "UNKNOWN_DUAL_BUDGET_PORTFOLIO_SCOPE_UNVERIFIED_V9"
            )
        ),
        "first_blocking_tier": first_blocking_tier,
        "source": {
            "portfolio_snapshot_preregistration_v9_hash": (
                preregistration_document.get(
                    "portfolio_snapshot_preregistration_v9_hash"
                )
                if preregistration_ok
                else None
            ),
            "proposal_scope_preregistration_v8_hash": (
                preregistration_source.get(
                    "proposal_scope_preregistration_v8_hash"
                )
                if predecessor_hash_ok
                else None
            ),
            "proposal_scope_reconciliation_v8_hash": (
                _dict(proposal_reconciliation_v8_document).get(
                    "proposal_scope_reconciliation_v8_hash"
                )
                if proposal_reconciliation_exact
                else None
            ),
            "dynamic_budget_consumer_v7_hash": (
                dynamic_v7_document.get("budget_consumer_v7_hash")
                if proposal_reconciliation_exact
                else None
            ),
            "legacy_budget_v11_hash": (
                legacy_v11_document.get("budget_v11_hash")
                if proposal_reconciliation_exact
                else None
            ),
            "legacy_snapshot_claim_hash": (
                snapshot_claim.get("snapshot_claim_hash")
                if snapshot_lineage_ok
                else None
            ),
            "legacy_snapshot_evidence_hash": (
                snapshot_evidence.get("snapshot_evidence_hash")
                if snapshot_lineage_ok
                else None
            ),
            "legacy_transition_hash": (
                transition.get("transition_hash")
                if snapshot_lineage_ok
                else None
            ),
            "dynamic_positions_before_hash": dynamic_positions_hash,
            "normalized_legacy_positions_hash": legacy_positions_hash,
        },
        "snapshot_scope": {
            "snapshot_position_semantics": SNAPSHOT_POSITION_SEMANTICS,
            "position_reconciliation_rule": POSITION_RECONCILIATION_RULE,
            "legacy_portfolio_unit_to_minor": scale,
            "snapshot_id_hash": (
                snapshot.get("snapshot_id_hash") if snapshot_lineage_ok else None
            ),
            "snapshot_sequence": (
                snapshot.get("snapshot_sequence") if snapshot_lineage_ok else None
            ),
            "observed_at_unix_ms": (
                snapshot.get("observed_at_unix_ms")
                if snapshot_lineage_ok
                else None
            ),
            "position_count": (
                len(legacy_positions) if legacy_positions is not None else None
            ),
            "dynamic_equity_minor": (
                dynamic_equity if type(dynamic_equity) is int else None
            ),
            "normalized_legacy_equity_minor": legacy_equity,
            "normalized_legacy_gross_notional_minor": legacy_gross_minor,
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "proposal_scope_reconciliation_v8_exact": (
                proposal_reconciliation_exact
            ),
            "proposal_scope_reconciled": proposal_reconciliation_pass,
            "portfolio_snapshot_lineage_recomputed": snapshot_lineage_ok,
            "positions_reconciled": position_scope_ok,
            "equity_reconciled": equity_scope_ok,
            "portfolio_snapshot_reconciled": portfolio_scope_exact,
            "combined_budget_scope_established": status == "PASS",
            "external_snapshot_provider_identity_verified": False,
            "snapshot_provider_implementation_verified": False,
            "snapshot_source_truth_verified": False,
            "snapshot_freshness_verified": False,
            "combined_admission_allowed": False,
            "runtime_consumer_bound": False,
            "execution_verified": False,
            "profitability_proven": False,
            "raw_positions_embedded": False,
            "raw_predecessor_context_embedded": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(
        document,
        "portfolio_snapshot_reconciliation_v9_hash",
    )


def verify_dual_budget_portfolio_snapshot_reconciliation_v9(
    document: Any,
    preregistration: Any,
    proposal_reconciliation_v8_document: Any,
    proposal_reconciliation_v8_context: Any,
    *,
    expected_portfolio_snapshot_preregistration_v9_hash: Any,
) -> dict[str, Any]:
    expected = evaluate_dual_budget_portfolio_snapshot_reconciliation_v9(
        preregistration,
        proposal_reconciliation_v8_document,
        proposal_reconciliation_v8_context,
        expected_portfolio_snapshot_preregistration_v9_hash=(
            expected_portfolio_snapshot_preregistration_v9_hash
        ),
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["portfolio_snapshot_v9_exact_rebuild_mismatch"],
        "portfolio_scope_status": expected["status"] if exact else "UNKNOWN",
        "combined_budget_status": (
            expected["combined_budget_status"] if exact else "NOT_ESTABLISHED"
        ),
        "combined_admission_status": "BLOCKED",
        "reconciliation_exactly_verified": exact,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "DualBudgetPortfolioSnapshotContractError",
    "POSITION_RECONCILIATION_RULE",
    "PREREGISTRATION_SCHEMA_VERSION",
    "RECONCILIATION_SCHEMA_VERSION",
    "SNAPSHOT_POSITION_SEMANTICS",
    "STATIC_FINGERPRINT",
    "VERIFICATION_SCHEMA_VERSION",
    "build_dual_budget_portfolio_snapshot_preregistration_v9",
    "evaluate_dual_budget_portfolio_snapshot_reconciliation_v9",
    "verify_dual_budget_portfolio_snapshot_preregistration_v9",
    "verify_dual_budget_portfolio_snapshot_reconciliation_v9",
]
