"""Bind correlation admission v2 to the effective-bet budget v3 decision.

The two predecessor contracts are independently exact and intentionally
unmodified. This consumer takes one strict snapshot of their shared source
documents, verifies both predecessors against that snapshot, and prevents a
correlation-admission PASS from being interpreted without the matching
portfolio budget decision.
"""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services.portfolio_correlation_admission_v2 import (
    SCHEMA_VERSION as ADMISSION_V2_SCHEMA_VERSION,
    verify_portfolio_correlation_admission_v2,
)
from exchange_terminal.services.strategy_correlation_cluster_effective_bet_budget_v3 import (
    BUDGET_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_effective_bet_budget_v3,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-binding-v1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260823-portfolio-correlation-admission-effective-budget-"
    "binding-v1-lock-1"
)
ADMISSION_V2_IMPLEMENTATION_SHA256 = (
    "a691435ceb366ba723ab1235467e4333da8bb622f10d826460ca104423b7a67f"
)
EFFECTIVE_BUDGET_V3_IMPLEMENTATION_SHA256 = (
    "bece44fe40c02242c879d1dead5cc11d2ce00edfc91c8d78a5b29962516c002d"
)
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = (
    "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"
)
DEFAULT_MAX_CLUSTER_GROSS_PCT = 45.0

TIER_ORDER = (
    "INPUT_SNAPSHOT",
    "ADMISSION_V2_EXACT",
    "EFFECTIVE_BUDGET_V3_EXACT",
    "CROSS_SOURCE_BINDING",
    "ADMISSION_V2_DECISION",
    "EFFECTIVE_BUDGET_V3_DECISION",
    "PERMISSION",
)

_HEX_CHARS = frozenset("0123456789abcdef")
_SOURCE_FIELDS = (
    "report_universe_contract_hash",
    "correlation_preregistration_hash",
    "correlation_matrix_hash",
    "complete_link_audit_hash",
    "complete_link_gate_hash",
    "strata_registration_hash",
    "strata_gate_hash",
    "admission_v2_hash",
    "effective_budget_v3_hash",
    "strategy_identity_hash",
    "proposal_scope_hash",
)


class _InvalidJsonDocument(ValueError):
    pass


def _plain_json_snapshot(
    value: Any,
    active: set[int] | None = None,
) -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise _InvalidJsonDocument("non-finite numbers are not supported")
        return value
    if type(value) not in (dict, list):
        raise _InvalidJsonDocument("document must contain exact JSON types")

    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        raise _InvalidJsonDocument("cyclic documents are not supported")
    active.add(identity)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise _InvalidJsonDocument("object keys must be exact strings")
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(identity)


def _hash_or_none(value: Any) -> str | None:
    if (
        type(value) is str
        and len(value) == 64
        and all(character in _HEX_CHARS for character in value)
    ):
        return value
    return None


def _nested_hash(document: Any, *path: str) -> str | None:
    current = document
    for key in path:
        if type(current) is not dict:
            return None
        current = current.get(key)
    return _hash_or_none(current)


def _safe_canonical_hash(value: Any) -> str | None:
    try:
        return strict_canonical_hash(value)
    except (TypeError, ValueError):
        return None


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "consumer_only": True,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "automatic_internal_backtest_activation_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _tier(
    name: str,
    state: str,
    detail: str,
) -> dict[str, str]:
    return {
        "tier": name,
        "state": state,
        "detail": detail,
    }


def _build_document(
    *,
    status: str,
    first_blocking_tier: str | None,
    admission_status: str,
    effective_budget_status: str,
    source: dict[str, str | None],
    checks: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    admission_exact = checks["admission_v2_exact"]
    budget_exact = checks["effective_budget_v3_exact"]
    cross_exact = checks["cross_source_hashes_exact"]

    tiers = [
        _tier(
            "INPUT_SNAPSHOT",
            "PASS" if checks["input_snapshot_exact"] else "BLOCK",
            "EXACT_JSON_SNAPSHOT"
            if checks["input_snapshot_exact"]
            else "SNAPSHOT_REJECTED",
        ),
        _tier(
            "ADMISSION_V2_EXACT",
            "PASS" if admission_exact else "BLOCK",
            "EXACT_REBUILD" if admission_exact else "UNKNOWN_OR_DRIFT",
        ),
        _tier(
            "EFFECTIVE_BUDGET_V3_EXACT",
            "PASS" if budget_exact else "BLOCK",
            "EXACT_REBUILD" if budget_exact else "UNKNOWN_OR_DRIFT",
        ),
        _tier(
            "CROSS_SOURCE_BINDING",
            "PASS" if cross_exact else "BLOCK",
            "ONE_SHARED_HASH_CHAIN"
            if cross_exact
            else "SHARED_HASH_CHAIN_UNPROVEN",
        ),
        _tier(
            "ADMISSION_V2_DECISION",
            admission_status if admission_exact else "NOT_EVALUATED",
            admission_status if admission_exact else "NOT_EVALUATED",
        ),
        _tier(
            "EFFECTIVE_BUDGET_V3_DECISION",
            effective_budget_status if budget_exact else "NOT_EVALUATED",
            effective_budget_status if budget_exact else "NOT_EVALUATED",
        ),
        _tier("PERMISSION", "PASS", "LOCKED"),
    ]

    document = {
        "schema_version": SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "binding_state": status,
        "first_blocking_tier": first_blocking_tier,
        "admission_v2_status": admission_status,
        "effective_budget_v3_status": effective_budget_status,
        "source": {field: source.get(field) for field in _SOURCE_FIELDS},
        "checks": checks,
        "tiers": tiers,
        "blockers": blockers,
        "policy": {
            "admission_v2_schema_version": ADMISSION_V2_SCHEMA_VERSION,
            "effective_budget_v3_schema_version": BUDGET_SCHEMA_VERSION,
            "admission_pass_without_budget_pass_allowed": False,
            "budget_pass_without_admission_pass_allowed": False,
            "one_shared_source_snapshot_required": True,
            "cross_hash_compatibility_fallback_allowed": False,
            "source_document_embedding_allowed": False,
        },
        "facts": {
            "admission_and_budget_independently_verified": (
                admission_exact and budget_exact
            ),
            "one_shared_source_snapshot_used": checks[
                "input_snapshot_exact"
            ],
            "source_documents_embedded": False,
            "positions_embedded": False,
            "proposed_symbol_embedded": False,
            "strategy_identity_embedded": False,
            "raw_symbol_lists_embedded": False,
            "runtime_gate_activated": False,
            "writer_implemented": False,
            "current_activated": False,
            "paper_authorized": False,
            "live_order_allowed": False,
            "profitability_proven": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "binding_hash")


def _snapshot_failure_document() -> dict[str, Any]:
    return _build_document(
        status="BLOCK",
        first_blocking_tier="INPUT_SNAPSHOT",
        admission_status="UNKNOWN",
        effective_budget_status="UNKNOWN",
        source={field: None for field in _SOURCE_FIELDS},
        checks={
            "input_snapshot_exact": False,
            "admission_v2_exact": False,
            "effective_budget_v3_exact": False,
            "report_universe_hash_bound": False,
            "correlation_preregistration_hash_bound": False,
            "shared_correlation_matrix_snapshot": False,
            "complete_link_audit_hash_bound": False,
            "complete_link_gate_hash_bound": False,
            "strata_hash_chain_bound": False,
            "strategy_identity_bound": False,
            "cross_source_hashes_exact": False,
            "admission_v2_decision_pass": False,
            "effective_budget_v3_decision_pass": False,
            "evidence_has_no_execution_authority": False,
        },
        blockers=["input_snapshot_failed"],
    )


def build_portfolio_correlation_admission_effective_budget_binding_v1(
    admission_v2_document: Any,
    effective_budget_v3_document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_audit_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    try:
        admission = _plain_json_snapshot(admission_v2_document)
        budget = _plain_json_snapshot(effective_budget_v3_document)
        report = _plain_json_snapshot(report_document)
        preregistration = _plain_json_snapshot(
            correlation_preregistration_document
        )
        matrix = _plain_json_snapshot(correlation_matrix_document)
        selection_cells = _plain_json_snapshot(selection_cells_document)
        complete_link_audit = _plain_json_snapshot(
            complete_link_audit_document
        )
        complete_link_gate = _plain_json_snapshot(
            complete_link_gate_document
        )
        strata_registration = _plain_json_snapshot(
            strata_preregistration_document
        )
        strata_gate = _plain_json_snapshot(strata_gate_document)
        clean_strategy_id = _plain_json_snapshot(strategy_id)
        clean_variant_id = _plain_json_snapshot(variant_id)
        clean_lane = _plain_json_snapshot(lane)
        clean_equity = _plain_json_snapshot(equity)
        clean_positions = _plain_json_snapshot(positions)
        clean_proposed_symbol = _plain_json_snapshot(proposed_symbol)
        clean_proposed_notional = _plain_json_snapshot(proposed_notional)
        clean_proposed_direction = _plain_json_snapshot(proposed_direction)
        clean_max_cluster_gross_pct = _plain_json_snapshot(
            max_cluster_gross_pct
        )
        clean_risk_increasing = _plain_json_snapshot(risk_increasing)
    except (TypeError, ValueError):
        return _snapshot_failure_document()

    try:
        admission_receipt = verify_portfolio_correlation_admission_v2(
            admission,
            report,
            preregistration,
            matrix,
            selection_cells,
            complete_link_gate,
            strata_registration,
            strata_gate,
            strategy_id=clean_strategy_id,
            variant_id=clean_variant_id,
            lane=clean_lane,
        )
    except (KeyError, TypeError, ValueError):
        admission_receipt = {}

    try:
        budget_receipt = (
            verify_strategy_correlation_cluster_effective_bet_budget_v3(
                budget,
                preregistration,
                matrix,
                complete_link_audit,
                strata_registration=strata_registration,
                strata_gate=strata_gate,
                complete_link_gate=complete_link_gate,
                equity=clean_equity,
                positions=clean_positions,
                proposed_symbol=clean_proposed_symbol,
                proposed_notional=clean_proposed_notional,
                proposed_direction=clean_proposed_direction,
                max_cluster_gross_pct=clean_max_cluster_gross_pct,
                risk_increasing=clean_risk_increasing,
            )
        )
    except (KeyError, TypeError, ValueError):
        budget_receipt = {}

    admission_hash = _nested_hash(admission, "correlation_admission_v2_hash")
    budget_hash = _nested_hash(budget, "budget_v3_hash")
    admission_exact = bool(
        type(admission_receipt) is dict
        and admission_receipt.get("status") == "PASS"
        and admission_hash is not None
    )
    budget_exact = bool(
        type(budget_receipt) is dict
        and budget_receipt.get("status") == "PASS"
        and budget_hash is not None
    )
    admission_status = (
        admission.get("status")
        if admission_exact and type(admission) is dict
        else "UNKNOWN"
    )
    budget_status = (
        budget.get("status")
        if budget_exact and type(budget) is dict
        else "UNKNOWN"
    )

    report_universe_hash = _nested_hash(
        report,
        "universe_contract",
        "contract_hash",
    )
    preregistration_hash = _nested_hash(
        preregistration,
        "preregistration_hash",
    )
    matrix_hash = _nested_hash(matrix, "matrix_hash")
    complete_link_audit_hash = _nested_hash(
        complete_link_audit,
        "audit_hash",
    )
    complete_link_gate_hash = _nested_hash(
        complete_link_gate,
        "gate_hash",
    )
    strata_registration_hash = _nested_hash(
        strata_registration,
        "registration_hash",
    )
    strata_gate_hash = _nested_hash(strata_gate, "gate_hash")

    strategy_identity_hash = _safe_canonical_hash(
        {
            "strategy_id": clean_strategy_id,
            "variant_id": clean_variant_id,
            "lane": clean_lane,
        }
    )
    proposal_scope_hash = _safe_canonical_hash(
        {
            "equity": clean_equity,
            "positions": clean_positions,
            "proposed_symbol": clean_proposed_symbol,
            "proposed_notional": clean_proposed_notional,
            "proposed_direction": clean_proposed_direction,
            "max_cluster_gross_pct": clean_max_cluster_gross_pct,
            "risk_increasing": clean_risk_increasing,
        }
    )

    admission_evidence = (
        admission.get("evidence_hashes")
        if type(admission) is dict
        and type(admission.get("evidence_hashes")) is dict
        else {}
    )
    budget_source = (
        budget.get("source")
        if type(budget) is dict and type(budget.get("source")) is dict
        else {}
    )
    gate_audit = (
        complete_link_gate.get("complete_link_audit")
        if type(complete_link_gate) is dict
        and type(complete_link_gate.get("complete_link_audit")) is dict
        else {}
    )

    report_universe_hash_bound = bool(
        admission_exact
        and report_universe_hash is not None
        and admission_evidence.get("report_universe_contract_hash")
        == report_universe_hash
    )
    correlation_preregistration_hash_bound = bool(
        admission_exact
        and budget_exact
        and preregistration_hash is not None
        and admission_evidence.get("correlation_preregistration_hash")
        == preregistration_hash
        and strata_registration.get("source_preregistration_hash")
        == preregistration_hash
        and strata_gate.get("source_preregistration_hash")
        == preregistration_hash
        and budget_source.get("same_source_preregistration_verified") is True
    )
    shared_correlation_matrix_snapshot = bool(
        admission_exact and budget_exact and matrix_hash is not None
    )
    complete_link_audit_hash_bound = bool(
        admission_exact
        and budget_exact
        and complete_link_audit_hash is not None
        and gate_audit.get("audit_hash") == complete_link_audit_hash
    )
    complete_link_gate_hash_bound = bool(
        admission_exact
        and budget_exact
        and complete_link_gate_hash is not None
        and budget_source.get("complete_link_gate_hash")
        == complete_link_gate_hash
        and strata_gate.get("base_complete_link_gate_hash")
        == complete_link_gate_hash
    )
    strata_hash_chain_bound = bool(
        admission_exact
        and budget_exact
        and strata_registration_hash is not None
        and strata_gate_hash is not None
        and budget_source.get("strata_registration_hash")
        == strata_registration_hash
        and budget_source.get("strata_gate_hash") == strata_gate_hash
        and strata_gate.get("strata_registration_hash")
        == strata_registration_hash
    )
    strategy_identity_bound = bool(
        admission_exact
        and budget_exact
        and strategy_identity_hash is not None
        and admission.get("strategy_id") == clean_strategy_id
        and admission.get("variant_id") == clean_variant_id
        and admission.get("lane") == clean_lane
        and complete_link_gate.get("strategy_id") == clean_strategy_id
        and complete_link_gate.get("variant_id") == clean_variant_id
        and complete_link_gate.get("lane") == clean_lane
        and strata_gate.get("strategy_id") == clean_strategy_id
        and strata_gate.get("variant_id") == clean_variant_id
        and strata_gate.get("lane") == clean_lane
    )
    cross_source_hashes_exact = all(
        (
            report_universe_hash_bound,
            correlation_preregistration_hash_bound,
            shared_correlation_matrix_snapshot,
            complete_link_audit_hash_bound,
            complete_link_gate_hash_bound,
            strata_hash_chain_bound,
            strategy_identity_bound,
            proposal_scope_hash is not None,
        )
    )

    evidence_has_no_execution_authority = bool(
        admission_exact
        and budget_exact
        and type(admission.get("permissions")) is dict
        and admission["permissions"].get("paper_authorized") is False
        and admission["permissions"].get("live_order_allowed") is False
        and type(budget.get("authority")) is dict
        and budget["authority"].get("current_admission_allowed") is False
        and budget["authority"].get("paper_authorized") is False
        and budget["authority"].get("live_order_allowed") is False
    )

    blockers: list[str] = []
    if not admission_exact:
        blockers.append("admission_v2_not_exact")
    if not budget_exact:
        blockers.append("effective_budget_v3_not_exact")
    if admission_exact and budget_exact and not cross_source_hashes_exact:
        blockers.append("cross_source_hash_binding_failed")
    if admission_exact and admission_status != "PASS":
        blockers.append("admission_v2_decision_blocked")
    if budget_exact and budget_status != "PASS":
        blockers.append("effective_budget_v3_decision_blocked")
    if admission_exact and budget_exact and not evidence_has_no_execution_authority:
        blockers.append("source_evidence_has_execution_authority")

    if not admission_exact:
        first_blocking_tier = "ADMISSION_V2_EXACT"
    elif not budget_exact:
        first_blocking_tier = "EFFECTIVE_BUDGET_V3_EXACT"
    elif not cross_source_hashes_exact:
        first_blocking_tier = "CROSS_SOURCE_BINDING"
    elif admission_status != "PASS":
        first_blocking_tier = "ADMISSION_V2_DECISION"
    elif budget_status != "PASS":
        first_blocking_tier = "EFFECTIVE_BUDGET_V3_DECISION"
    elif not evidence_has_no_execution_authority:
        first_blocking_tier = "PERMISSION"
    else:
        first_blocking_tier = None

    checks = {
        "input_snapshot_exact": True,
        "admission_v2_exact": admission_exact,
        "effective_budget_v3_exact": budget_exact,
        "report_universe_hash_bound": report_universe_hash_bound,
        "correlation_preregistration_hash_bound": (
            correlation_preregistration_hash_bound
        ),
        "shared_correlation_matrix_snapshot": (
            shared_correlation_matrix_snapshot
        ),
        "complete_link_audit_hash_bound": complete_link_audit_hash_bound,
        "complete_link_gate_hash_bound": complete_link_gate_hash_bound,
        "strata_hash_chain_bound": strata_hash_chain_bound,
        "strategy_identity_bound": strategy_identity_bound,
        "cross_source_hashes_exact": cross_source_hashes_exact,
        "admission_v2_decision_pass": admission_status == "PASS",
        "effective_budget_v3_decision_pass": budget_status == "PASS",
        "evidence_has_no_execution_authority": (
            evidence_has_no_execution_authority
        ),
    }
    source = {
        "report_universe_contract_hash": report_universe_hash,
        "correlation_preregistration_hash": preregistration_hash,
        "correlation_matrix_hash": matrix_hash,
        "complete_link_audit_hash": complete_link_audit_hash,
        "complete_link_gate_hash": complete_link_gate_hash,
        "strata_registration_hash": strata_registration_hash,
        "strata_gate_hash": strata_gate_hash,
        "admission_v2_hash": admission_hash,
        "effective_budget_v3_hash": budget_hash,
        "strategy_identity_hash": strategy_identity_hash,
        "proposal_scope_hash": proposal_scope_hash,
    }
    return _build_document(
        status="PASS" if first_blocking_tier is None else "BLOCK",
        first_blocking_tier=first_blocking_tier,
        admission_status=admission_status,
        effective_budget_status=budget_status,
        source=source,
        checks=checks,
        blockers=blockers,
    )


def verify_portfolio_correlation_admission_effective_budget_binding_v1(
    document: Any,
    admission_v2_document: Any,
    effective_budget_v3_document: Any,
    report_document: Any,
    correlation_preregistration_document: Any,
    correlation_matrix_document: Any,
    selection_cells_document: Any,
    complete_link_audit_document: Any,
    complete_link_gate_document: Any,
    strata_preregistration_document: Any,
    strata_gate_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = True,
) -> dict[str, Any]:
    expected = build_portfolio_correlation_admission_effective_budget_binding_v1(
        admission_v2_document,
        effective_budget_v3_document,
        report_document,
        correlation_preregistration_document,
        correlation_matrix_document,
        selection_cells_document,
        complete_link_audit_document,
        complete_link_gate_document,
        strata_preregistration_document,
        strata_gate_document,
        strategy_id=strategy_id,
        variant_id=variant_id,
        lane=lane,
        equity=equity,
        positions=positions,
        proposed_symbol=proposed_symbol,
        proposed_notional=proposed_notional,
        proposed_direction=proposed_direction,
        max_cluster_gross_pct=max_cluster_gross_pct,
        risk_increasing=risk_increasing,
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "binding_status": expected["status"] if exact else "UNKNOWN",
        "binding_hash": expected["binding_hash"] if exact else None,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
