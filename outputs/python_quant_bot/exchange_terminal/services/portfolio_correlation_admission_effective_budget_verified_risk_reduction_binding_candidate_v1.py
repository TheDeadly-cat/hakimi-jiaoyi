"""Bind a conservative legacy block to a verified v4 risk reduction.

This pure in-memory candidate does not replace binding-v1.  It recognizes only
the narrow case where binding-v1 is exact and blocks solely because v3 omits
the strata source chain on its caller-declared risk-reduction path, while v4
independently proves an exact opposite-side, no-cross position reduction.
"""

from __future__ import annotations

import math
from typing import Any

from exchange_terminal.services import (
    portfolio_correlation_admission_effective_budget_binding_v1 as binding_v1,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_effective_bet_budget_v4 as budget_v4,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


SCHEMA_VERSION = (
    "portfolio-correlation-admission-effective-budget-verified-risk-reduction-"
    "binding-candidate-v1"
)
VERIFICATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260825-verified-risk-reduction-effective-budget-binding-"
    "candidate-v1-unbound-lock-1"
)
BINDING_V1_IMPLEMENTATION_SHA256 = "7263b07df309ad3c2a4c79313e62ff8912c567ee0cf6a2ee9abdc336ce6bd9e9"
BUDGET_V4_IMPLEMENTATION_SHA256 = "f32239e4d3c2c5a015044ad2e5f8522b093b45746056f0656437cc92b23955f2"
STRICT_CANONICAL_IMPLEMENTATION_SHA256 = "cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412"

TIER_ORDER = (
    "INPUT_SNAPSHOT",
    "RISK_REDUCTION_LANE",
    "LEGACY_BINDING_EXACT",
    "LEGACY_CONSERVATIVE_BLOCK",
    "EFFECTIVE_BUDGET_V4_EXACT",
    "VERIFIED_TRANSITION",
    "CROSS_VERSION_BINDING",
    "PERMISSION",
)
ACTIVATION_ORDER = (
    "SYNTHETIC_GAP_EVIDENCE",
    "CANDIDATE_CONTRACT",
    "ADVERSARIAL_REVIEW",
    "READONLY_CONSUMER_PREREGISTRATION",
    "SEPARATE_CURRENT_DECISION",
)
EXPECTED_LEGACY_BLOCKERS = ("cross_source_hash_binding_failed",)
_HEX = frozenset("0123456789abcdef")


class VerifiedRiskReductionBindingCandidateError(ValueError):
    pass


def _plain_json_snapshot(value: Any, active: set[int] | None = None) -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise VerifiedRiskReductionBindingCandidateError(
                "non-finite values are not supported"
            )
        return value
    if type(value) not in (dict, list):
        raise VerifiedRiskReductionBindingCandidateError(
            "inputs must use exact JSON types"
        )
    active = set() if active is None else active
    marker = id(value)
    if marker in active:
        raise VerifiedRiskReductionBindingCandidateError(
            "cyclic inputs are not supported"
        )
    active.add(marker)
    try:
        if type(value) is list:
            return [_plain_json_snapshot(item, active) for item in value]
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise VerifiedRiskReductionBindingCandidateError(
                    "object keys must be exact strings"
                )
            snapshot[key] = _plain_json_snapshot(item, active)
        return snapshot
    finally:
        active.remove(marker)


def _hash_or_none(value: Any) -> str | None:
    if (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in _HEX for character in value)
    ):
        return value
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


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


def _build_document(
    *,
    checks: dict[str, bool],
    source: dict[str, str | None],
    first_blocking_tier: str | None,
    blockers: list[str],
) -> dict[str, Any]:
    passed = first_blocking_tier is None
    return seal_strict_canonical_document(
        {
            "schema_version": SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "PASS" if passed else "BLOCKED",
            "admission_status": "BLOCKED",
            "decision": (
                "VERIFIED_RISK_REDUCTION_OBSERVED_CONSUMER_CANDIDATE"
                if passed
                else "BLOCK_VERIFIED_RISK_REDUCTION_BINDING_CANDIDATE"
            ),
            "first_blocking_tier": first_blocking_tier,
            "source": source,
            "checks": checks,
            "facts": {
                "legacy_v3_caller_flag_bypass_observed": checks[
                    "legacy_conservative_block_exact"
                ],
                "legacy_current_consumer_fail_closed": checks[
                    "legacy_conservative_block_exact"
                ],
                "risk_reduction_derived_from_position_transition": checks[
                    "verified_transition_pass"
                ],
                "caller_risk_reduction_flag_sufficient": False,
                "legacy_binding_replaced": False,
                "current_activated": False,
                "runtime_gate_integrated": False,
                "source_documents_embedded": False,
                "position_rows_embedded": False,
                "transition_document_embedded": False,
                "profitability_proven": False,
                "runtime_assets_accessed": False,
                "network_accessed": False,
            },
            "policy": {
                "candidate_scope": "VERIFIED_RISK_REDUCTION_ONLY",
                "legacy_binding_must_be_exact": True,
                "legacy_block_must_be_cross_source_only": True,
                "effective_budget_v4_must_pass": True,
                "caller_flag_only_bypass_allowed": False,
                "same_direction_add_allowed": False,
                "cross_zero_or_reversal_allowed": False,
                "precomputed_predecessor_result_accepted": False,
            },
            "activation_order": list(ACTIVATION_ORDER),
            "blockers": blockers,
            "limitations": [
                "POSITION_SNAPSHOT_PROVENANCE_UNVERIFIED",
                "SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
                "EXECUTION_UNVERIFIED",
                "CURRENT_ACTIVATION_UNAUTHORIZED",
            ],
            "authority": _authority(),
        },
        "candidate_hash",
    )


def _snapshot_failure_document() -> dict[str, Any]:
    checks = {
        "input_snapshot_exact": False,
        "risk_reduction_lane_exact": False,
        "legacy_binding_exact": False,
        "legacy_conservative_block_exact": False,
        "effective_budget_v4_exact": False,
        "verified_transition_pass": False,
        "cross_version_binding_exact": False,
        "source_authority_locked": False,
    }
    return _build_document(
        checks=checks,
        source={
            "legacy_binding_hash": None,
            "admission_v2_hash": None,
            "effective_budget_v3_hash": None,
            "effective_budget_v4_hash": None,
            "risk_reduction_transition_hash": None,
            "proposal_scope_hash": None,
            "binding_v1_implementation_sha256": (
                BINDING_V1_IMPLEMENTATION_SHA256
            ),
            "budget_v4_implementation_sha256": BUDGET_V4_IMPLEMENTATION_SHA256,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        first_blocking_tier="INPUT_SNAPSHOT",
        blockers=["input_snapshot_failed"],
    )


def build_verified_risk_reduction_effective_budget_binding_candidate_v1(
    legacy_binding_document: Any,
    effective_budget_v4_document: Any,
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
    positions_after: Any,
    risk_reduction_transition_document: Any,
    *,
    strategy_id: Any,
    variant_id: Any,
    lane: Any,
    equity: Any,
    positions: Any,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = binding_v1.DEFAULT_MAX_CLUSTER_GROSS_PCT,
    risk_increasing: Any = False,
) -> dict[str, Any]:
    try:
        snapshot = _plain_json_snapshot(
            {
                "legacy_binding": legacy_binding_document,
                "budget_v4": effective_budget_v4_document,
                "admission_v2": admission_v2_document,
                "budget_v3": effective_budget_v3_document,
                "report": report_document,
                "preregistration": correlation_preregistration_document,
                "matrix": correlation_matrix_document,
                "selection_cells": selection_cells_document,
                "complete_link_audit": complete_link_audit_document,
                "complete_link_gate": complete_link_gate_document,
                "strata_registration": strata_preregistration_document,
                "strata_gate": strata_gate_document,
                "positions_after": positions_after,
                "transition": risk_reduction_transition_document,
                "strategy_id": strategy_id,
                "variant_id": variant_id,
                "lane": lane,
                "equity": equity,
                "positions": positions,
                "proposed_symbol": proposed_symbol,
                "proposed_notional": proposed_notional,
                "proposed_direction": proposed_direction,
                "max_cluster_gross_pct": max_cluster_gross_pct,
                "risk_increasing": risk_increasing,
            }
        )
    except (TypeError, ValueError):
        return _snapshot_failure_document()

    legacy = _mapping(snapshot["legacy_binding"])
    budget4 = _mapping(snapshot["budget_v4"])
    admission = _mapping(snapshot["admission_v2"])
    budget3 = _mapping(snapshot["budget_v3"])
    transition = _mapping(snapshot["transition"])
    legacy_checks = _mapping(legacy.get("checks"))
    legacy_source = _mapping(legacy.get("source"))
    legacy_authority = _mapping(legacy.get("authority"))
    v4_checks = _mapping(budget4.get("checks"))
    v4_facts = _mapping(budget4.get("facts"))
    v4_source = _mapping(budget4.get("source"))
    v4_authority = _mapping(budget4.get("authority"))

    try:
        legacy_receipt = (
            binding_v1.verify_portfolio_correlation_admission_effective_budget_binding_v1(
                legacy,
                admission,
                budget3,
                snapshot["report"],
                snapshot["preregistration"],
                snapshot["matrix"],
                snapshot["selection_cells"],
                snapshot["complete_link_audit"],
                snapshot["complete_link_gate"],
                snapshot["strata_registration"],
                snapshot["strata_gate"],
                strategy_id=snapshot["strategy_id"],
                variant_id=snapshot["variant_id"],
                lane=snapshot["lane"],
                equity=snapshot["equity"],
                positions=snapshot["positions"],
                proposed_symbol=snapshot["proposed_symbol"],
                proposed_notional=snapshot["proposed_notional"],
                proposed_direction=snapshot["proposed_direction"],
                max_cluster_gross_pct=snapshot["max_cluster_gross_pct"],
                risk_increasing=snapshot["risk_increasing"],
            )
        )
    except Exception:
        legacy_receipt = {}
    legacy_binding_exact = bool(
        type(legacy_receipt) is dict
        and legacy_receipt.get("status") == "PASS"
        and _hash_or_none(legacy.get("binding_hash")) is not None
    )

    try:
        v4_receipt = budget_v4.verify_strategy_correlation_cluster_effective_bet_budget_v4(
            budget4,
            snapshot["preregistration"],
            snapshot["matrix"],
            snapshot["complete_link_audit"],
            strata_registration=snapshot["strata_registration"],
            strata_gate=snapshot["strata_gate"],
            complete_link_gate=snapshot["complete_link_gate"],
            equity=snapshot["equity"],
            positions=snapshot["positions"],
            proposed_symbol=snapshot["proposed_symbol"],
            proposed_notional=snapshot["proposed_notional"],
            proposed_direction=snapshot["proposed_direction"],
            max_cluster_gross_pct=snapshot["max_cluster_gross_pct"],
            risk_increasing=snapshot["risk_increasing"],
            positions_after=snapshot["positions_after"],
            risk_reduction_transition=transition,
        )
    except Exception:
        v4_receipt = {}
    effective_budget_v4_exact = bool(
        type(v4_receipt) is dict
        and v4_receipt.get("status") == "PASS"
        and _hash_or_none(budget4.get("budget_v4_hash")) is not None
    )

    risk_reduction_lane_exact = snapshot["risk_increasing"] is False
    legacy_conservative_block_exact = bool(
        legacy_binding_exact
        and legacy.get("status") == "BLOCK"
        and legacy.get("first_blocking_tier") == "CROSS_SOURCE_BINDING"
        and legacy.get("blockers") == list(EXPECTED_LEGACY_BLOCKERS)
        and legacy.get("admission_v2_status") == "PASS"
        and legacy.get("effective_budget_v3_status") == "PASS"
        and legacy_checks.get("admission_v2_exact") is True
        and legacy_checks.get("effective_budget_v3_exact") is True
        and legacy_checks.get("admission_v2_decision_pass") is True
        and legacy_checks.get("effective_budget_v3_decision_pass") is True
        and legacy_checks.get("cross_source_hashes_exact") is False
    )
    verified_transition_pass = bool(
        effective_budget_v4_exact
        and budget4.get("status") == "PASS"
        and budget4.get("decision")
        == "PASS_VERIFIED_RISK_REDUCTION_TRANSITION"
        and v4_checks.get("verified_risk_reduction_transition") is True
        and v4_checks.get("caller_flag_only_bypass_rejected") is True
        and v4_facts.get("risk_reduction_derived_from_position_transition")
        is True
        and v4_facts.get("caller_risk_reduction_flag_sufficient") is False
    )

    proposal_scope_hash = strict_canonical_hash(
        {
            "equity": snapshot["equity"],
            "positions": snapshot["positions"],
            "proposed_symbol": snapshot["proposed_symbol"],
            "proposed_notional": snapshot["proposed_notional"],
            "proposed_direction": snapshot["proposed_direction"],
            "max_cluster_gross_pct": snapshot["max_cluster_gross_pct"],
            "risk_increasing": snapshot["risk_increasing"],
        }
    )
    admission_hash = _hash_or_none(
        admission.get("correlation_admission_v2_hash")
    )
    v3_hash = _hash_or_none(budget3.get("budget_v3_hash"))
    v4_hash = _hash_or_none(budget4.get("budget_v4_hash"))
    transition_hash = _hash_or_none(transition.get("transition_hash"))
    cross_version_binding_exact = bool(
        legacy_binding_exact
        and effective_budget_v4_exact
        and admission_hash is not None
        and v3_hash is not None
        and v4_hash is not None
        and transition_hash is not None
        and legacy_source.get("admission_v2_hash") == admission_hash
        and legacy_source.get("effective_budget_v3_hash") == v3_hash
        and legacy_source.get("proposal_scope_hash") == proposal_scope_hash
        and v4_source.get("v3_budget_hash") == v3_hash
        and v4_source.get("risk_reduction_transition_hash")
        == transition_hash
        and v4_source.get("v3_decision") == "RISK_REDUCTION_PATH"
    )
    source_authority_locked = bool(
        legacy_binding_exact
        and effective_budget_v4_exact
        and legacy_authority.get("writer_allowed") is False
        and legacy_authority.get("current_admission_allowed") is False
        and legacy_authority.get("paper_authorized") is False
        and legacy_authority.get("live_order_allowed") is False
        and v4_authority.get("writer_allowed") is False
        and v4_authority.get("current_admission_allowed") is False
        and v4_authority.get("paper_authorized") is False
        and v4_authority.get("live_order_allowed") is False
    )
    checks = {
        "input_snapshot_exact": True,
        "risk_reduction_lane_exact": risk_reduction_lane_exact,
        "legacy_binding_exact": legacy_binding_exact,
        "legacy_conservative_block_exact": legacy_conservative_block_exact,
        "effective_budget_v4_exact": effective_budget_v4_exact,
        "verified_transition_pass": verified_transition_pass,
        "cross_version_binding_exact": cross_version_binding_exact,
        "source_authority_locked": source_authority_locked,
    }
    failures = (
        ("risk_reduction_lane_exact", "RISK_REDUCTION_LANE", "risk_reduction_lane_required"),
        ("legacy_binding_exact", "LEGACY_BINDING_EXACT", "legacy_binding_not_exact"),
        (
            "legacy_conservative_block_exact",
            "LEGACY_CONSERVATIVE_BLOCK",
            "legacy_binding_not_conservative_cross_source_block",
        ),
        (
            "effective_budget_v4_exact",
            "EFFECTIVE_BUDGET_V4_EXACT",
            "effective_budget_v4_not_exact",
        ),
        (
            "verified_transition_pass",
            "VERIFIED_TRANSITION",
            "verified_risk_reduction_transition_not_pass",
        ),
        (
            "cross_version_binding_exact",
            "CROSS_VERSION_BINDING",
            "cross_version_binding_failed",
        ),
        (
            "source_authority_locked",
            "PERMISSION",
            "source_authority_not_locked",
        ),
    )
    blockers: list[str] = []
    first_blocking_tier: str | None = None
    for check_name, tier, blocker in failures:
        if checks[check_name] is False:
            blockers.append(blocker)
            if first_blocking_tier is None:
                first_blocking_tier = tier
    return _build_document(
        checks=checks,
        source={
            "legacy_binding_hash": _hash_or_none(legacy.get("binding_hash")),
            "admission_v2_hash": admission_hash,
            "effective_budget_v3_hash": v3_hash,
            "effective_budget_v4_hash": v4_hash,
            "risk_reduction_transition_hash": transition_hash,
            "proposal_scope_hash": proposal_scope_hash,
            "binding_v1_implementation_sha256": (
                BINDING_V1_IMPLEMENTATION_SHA256
            ),
            "budget_v4_implementation_sha256": BUDGET_V4_IMPLEMENTATION_SHA256,
            "strict_canonical_implementation_sha256": (
                STRICT_CANONICAL_IMPLEMENTATION_SHA256
            ),
        },
        first_blocking_tier=first_blocking_tier,
        blockers=blockers,
    )


def verify_verified_risk_reduction_effective_budget_binding_candidate_v1(
    document: Any,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        snapshot = _plain_json_snapshot(document)
        expected = (
            build_verified_risk_reduction_effective_budget_binding_candidate_v1(
                *args, **kwargs
            )
        )
        exact = strict_json_contract_equal(snapshot, expected)
    except Exception:
        exact = False
        expected = None
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "candidate_status": expected["status"] if exact else "UNKNOWN",
        "candidate_hash": expected["candidate_hash"] if exact else None,
        "runtime_gate_activation_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "ACTIVATION_ORDER",
    "BINDING_V1_IMPLEMENTATION_SHA256",
    "BUDGET_V4_IMPLEMENTATION_SHA256",
    "EXPECTED_LEGACY_BLOCKERS",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STRICT_CANONICAL_IMPLEMENTATION_SHA256",
    "TIER_ORDER",
    "VERIFICATION_SCHEMA_VERSION",
    "VerifiedRiskReductionBindingCandidateError",
    "build_verified_risk_reduction_effective_budget_binding_candidate_v1",
    "verify_verified_risk_reduction_effective_budget_binding_candidate_v1",
]
