"""Unmounted ADR0345 prerequisite for the geometry-bound effective budget.

The binding never reclusters a preregistered portfolio.  For risk-increasing
research requests, an exact ADR0345 PASS is required before the existing
geometry-bound budget verifier may run.  An exact BLOCK therefore forces a new
preregistration instead of allowing related assets to remain separate tickets.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1 as _budget_binding,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_cluster_gate_v1 as _uncertainty_gate,
)


SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-effective-bet-budget-"
    "binding-contract-v1"
)
PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-effective-bet-budget-"
    "binding-preregistration-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-effective-bet-budget-"
    "binding-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-uncertainty-multi-window-effective-bet-"
    "budget-binding-v1-synthetic-unmounted-veto-lock-1"
)
UNCERTAINTY_GATE_SOURCE_SHA256 = (
    "4c64530efa76730404b7441ecdb9dab9ee914c156116296eea21a54c47a5f9e2"
)
GEOMETRY_BUDGET_BINDING_SOURCE_SHA256 = (
    "d728150d3ab2d9dd8b998b23d789cb59de2a220274e87b986e4343d5dd9258b3"
)
EFFECTIVE_BUDGET_V3_SOURCE_SHA256 = (
    "bece44fe40c02242c879d1dead5cc11d2ce00edfc91c8d78a5b29962516c002d"
)
ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_BINDING_PREREGISTRATION",
    "VERIFY_EXACT_MULTI_WINDOW_UNCERTAINTY_CLUSTER_GATE",
    "VETO_RISK_INCREASE_ON_CROSS_CLUSTER_DEPENDENCE",
    "VERIFY_EXACT_GEOMETRY_BOUND_EFFECTIVE_BUDGET",
    "REQUIRE_EXACT_RISK_REDUCTION_DECISION_FOR_REDUCTION_EXCEPTION",
    "PRESERVE_RESEARCH_ONLY_AUTHORITY_LOCK",
)

_UNCERTAINTY_PREREGISTRATION_CONTEXT_KEYS = frozenset(
    {
        "expected_symbols",
        "expected_clusters",
        "expected_windows",
        "expected_preregistration_hash",
    }
)
_BUDGET_PREREGISTRATION_CONTEXT_KEYS = frozenset(
    {
        "geometry_complete_link_binding_preregistration",
        "geometry_preregistration",
        "cluster_preregistration",
        "strata_registration",
        "expected_budget_binding_preregistration_hash",
        "expected_geometry_complete_link_binding_preregistration_hash",
        "expected_geometry_preregistration_hash",
        "expected_cluster_preregistration_hash",
        "expected_strata_registration_hash",
    }
)
_UNCERTAINTY_GATE_CONTEXT_KEYS = frozenset(
    {
        "uncertainty_preregistration",
        "window_audits",
        "expected_gate_hash",
        "expected_preregistration_hash",
        "expected_window_audit_hashes",
    }
)
_BUDGET_EVALUATION_CONTEXT_KEYS = frozenset(
    {
        "budget_binding_preregistration",
        "geometry_complete_link_binding_preregistration",
        "geometry_preregistration",
        "geometry_gate_document",
        "geometry_complete_link_binding_evaluation",
        "cluster_preregistration",
        "correlation_matrix",
        "selection_cells",
        "strata_registration",
        "strata_gate",
        "expected_evaluation_hash",
        "expected_budget_binding_preregistration_hash",
        "expected_geometry_complete_link_binding_preregistration_hash",
        "expected_geometry_preregistration_hash",
        "expected_cluster_preregistration_hash",
        "expected_strata_registration_hash",
        "expected_geometry_complete_link_binding_evaluation_hash",
        "strategy_id",
        "variant_id",
        "lane",
        "equity",
        "positions",
        "proposed_symbol",
        "proposed_notional",
        "proposed_direction",
        "max_cluster_gross_pct",
        "risk_increasing",
    }
)
_BASE_BLOCKERS = (
    "UNMOUNTED_CANDIDATE",
    "NO_RUNTIME_CONSUMER_BOUND",
    "WINDOW_LABEL_ISSUER_BINDING_UNPROVEN",
    "CURRENT_ADMISSION_LOCKED",
    "PAPER_LIVE_UNAUTHORIZED",
)


def _canonical_hash(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


def _seal(document: dict[str, Any], field: str) -> dict[str, Any]:
    result = dict(document)
    result[field] = _canonical_hash(document)
    return result


def _exact_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_hash(document: Any, field: str) -> str | None:
    if type(document) is not dict:
        return None
    value = document.get(field)
    return value if _exact_hash(value) else None


def _exact_context(value: Any, keys: frozenset[str]) -> bool:
    return type(value) is dict and frozenset(value) == keys


def _authority() -> dict[str, bool]:
    return {
        "research_evidence_only": True,
        "current_admission_allowed": False,
        "effective_budget_activation_allowed": False,
        "http_registration_allowed": False,
        "runtime_activation_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


_CONTRACT_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "activation_sequence": list(ACTIVATION_SEQUENCE),
    "uncertainty_gate": {
        "module": (
            "exchange_terminal.services."
            "strategy_correlation_uncertainty_multi_window_cluster_gate_v1"
        ),
        "source_sha256": UNCERTAINTY_GATE_SOURCE_SHA256,
        "contract_hash": _uncertainty_gate.GATE_CONTRACT_HASH,
        "static_fingerprint": _uncertainty_gate.STATIC_FINGERPRINT,
        "verifier": (
            "verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1"
        ),
    },
    "geometry_budget_binding": {
        "module": (
            "exchange_terminal.services."
            "strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1"
        ),
        "source_sha256": GEOMETRY_BUDGET_BINDING_SOURCE_SHA256,
        "contract_hash": _budget_binding.BINDING_CONTRACT_HASH,
        "static_fingerprint": _budget_binding.STATIC_FINGERPRINT,
        "effective_budget_v3_source_sha256": EFFECTIVE_BUDGET_V3_SOURCE_SHA256,
        "verifier": (
            "verify_strategy_correlation_matrix_geometry_effective_bet_budget_"
            "binding_evaluation_v1"
        ),
    },
    "risk_increasing_rule": "ADR0345_PASS_REQUIRED_BEFORE_BUDGET_VERIFICATION",
    "risk_reduction_rule": (
        "ADR0345_EXACT_AND_BUDGET_DECISION_RISK_REDUCTION_PATH_REQUIRED"
    ),
    "partition_rule": "NO_DYNAMIC_RECLUSTERING_REPREREGISTRATION_REQUIRED",
    "authority": _authority(),
}
BINDING_CONTRACT_HASH = _canonical_hash(_CONTRACT_MANIFEST)


def _verify_uncertainty_preregistration(
    document: Any,
    context: Any,
) -> bool:
    if not _exact_context(context, _UNCERTAINTY_PREREGISTRATION_CONTEXT_KEYS):
        return False
    try:
        return _uncertainty_gate.verify_strategy_correlation_uncertainty_multi_window_cluster_preregistration_v1(
            document,
            expected_symbols=context["expected_symbols"],
            expected_clusters=context["expected_clusters"],
            expected_windows=context["expected_windows"],
            expected_preregistration_hash=context[
                "expected_preregistration_hash"
            ],
        )
    except Exception:
        return False


def _verify_budget_preregistration(document: Any, context: Any) -> bool:
    if not _exact_context(context, _BUDGET_PREREGISTRATION_CONTEXT_KEYS):
        return False
    try:
        return _budget_binding.verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_preregistration_v1(
            document,
            context["geometry_complete_link_binding_preregistration"],
            context["geometry_preregistration"],
            context["cluster_preregistration"],
            context["strata_registration"],
            expected_budget_binding_preregistration_hash=context[
                "expected_budget_binding_preregistration_hash"
            ],
            expected_geometry_complete_link_binding_preregistration_hash=context[
                "expected_geometry_complete_link_binding_preregistration_hash"
            ],
            expected_geometry_preregistration_hash=context[
                "expected_geometry_preregistration_hash"
            ],
            expected_cluster_preregistration_hash=context[
                "expected_cluster_preregistration_hash"
            ],
            expected_strata_registration_hash=context[
                "expected_strata_registration_hash"
            ],
        )
    except Exception:
        return False


def build_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1(
    uncertainty_preregistration: Any,
    budget_binding_preregistration: Any,
    *,
    uncertainty_preregistration_verification_context: Any,
    budget_preregistration_verification_context: Any,
) -> dict[str, Any] | None:
    if not _verify_uncertainty_preregistration(
        uncertainty_preregistration,
        uncertainty_preregistration_verification_context,
    ) or not _verify_budget_preregistration(
        budget_binding_preregistration,
        budget_preregistration_verification_context,
    ):
        return None
    cluster_preregistration = budget_preregistration_verification_context.get(
        "cluster_preregistration"
    )
    expected_symbols = uncertainty_preregistration_verification_context.get(
        "expected_symbols"
    )
    expected_clusters = uncertainty_preregistration_verification_context.get(
        "expected_clusters"
    )
    if (
        type(cluster_preregistration) is not dict
        or cluster_preregistration.get("symbols") != expected_symbols
        or cluster_preregistration.get("clusters") != expected_clusters
        or uncertainty_preregistration.get("cluster_partition_hash")
        != _canonical_hash(expected_clusters)
        or budget_binding_preregistration.get("cluster_preregistration_hash")
        != budget_preregistration_verification_context.get(
            "expected_cluster_preregistration_hash"
        )
    ):
        return None
    document = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "uncertainty_gate_contract_hash": _uncertainty_gate.GATE_CONTRACT_HASH,
        "geometry_budget_binding_contract_hash": (
            _budget_binding.BINDING_CONTRACT_HASH
        ),
        "uncertainty_preregistration_hash": (
            uncertainty_preregistration_verification_context[
                "expected_preregistration_hash"
            ]
        ),
        "budget_binding_preregistration_hash": (
            budget_preregistration_verification_context[
                "expected_budget_binding_preregistration_hash"
            ]
        ),
        "cluster_preregistration_hash": (
            budget_preregistration_verification_context[
                "expected_cluster_preregistration_hash"
            ]
        ),
        "shared_symbol_order_hash": uncertainty_preregistration[
            "symbol_order_hash"
        ],
        "shared_cluster_partition_hash": uncertainty_preregistration[
            "cluster_partition_hash"
        ],
        "window_order_hash": uncertainty_preregistration["window_order_hash"],
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "facts": {
            "shared_symbols_exact": True,
            "shared_cluster_partition_exact": True,
            "dynamic_reclustering_allowed": False,
            "risk_increase_requires_uncertainty_gate_pass": True,
            "synthetic_only": True,
            "mounted": False,
        },
        "blockers": list(_BASE_BLOCKERS),
        "authority": _authority(),
    }
    return _seal(document, "preregistration_hash")


def verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1(
    document: Any,
    uncertainty_preregistration: Any,
    budget_binding_preregistration: Any,
    *,
    expected_preregistration_hash: Any,
    uncertainty_preregistration_verification_context: Any,
    budget_preregistration_verification_context: Any,
) -> bool:
    if type(document) is not dict or not _exact_hash(expected_preregistration_hash):
        return False
    expected = build_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1(
        uncertainty_preregistration,
        budget_binding_preregistration,
        uncertainty_preregistration_verification_context=(
            uncertainty_preregistration_verification_context
        ),
        budget_preregistration_verification_context=(
            budget_preregistration_verification_context
        ),
    )
    return bool(
        expected is not None
        and document == expected
        and document.get("preregistration_hash") == expected_preregistration_hash
        and compare_digest(expected["preregistration_hash"], expected_preregistration_hash)
    )


def _uncertainty_gate_exact(document: Any, context: Any) -> bool:
    if not _exact_context(context, _UNCERTAINTY_GATE_CONTEXT_KEYS):
        return False
    try:
        return _uncertainty_gate.verify_strategy_correlation_uncertainty_multi_window_cluster_gate_v1(
            document,
            context["uncertainty_preregistration"],
            context["window_audits"],
            expected_gate_hash=context["expected_gate_hash"],
            expected_preregistration_hash=context[
                "expected_preregistration_hash"
            ],
            expected_window_audit_hashes=context[
                "expected_window_audit_hashes"
            ],
        )
    except Exception:
        return False


def _budget_evaluation_exact(document: Any, context: Any) -> bool:
    if not _exact_context(context, _BUDGET_EVALUATION_CONTEXT_KEYS):
        return False
    try:
        return _budget_binding.verify_strategy_correlation_matrix_geometry_effective_bet_budget_binding_evaluation_v1(
            document,
            context["budget_binding_preregistration"],
            context["geometry_complete_link_binding_preregistration"],
            context["geometry_preregistration"],
            context["geometry_gate_document"],
            context["geometry_complete_link_binding_evaluation"],
            context["cluster_preregistration"],
            context["correlation_matrix"],
            context["selection_cells"],
            context["strata_registration"],
            context["strata_gate"],
            expected_evaluation_hash=context["expected_evaluation_hash"],
            expected_budget_binding_preregistration_hash=context[
                "expected_budget_binding_preregistration_hash"
            ],
            expected_geometry_complete_link_binding_preregistration_hash=context[
                "expected_geometry_complete_link_binding_preregistration_hash"
            ],
            expected_geometry_preregistration_hash=context[
                "expected_geometry_preregistration_hash"
            ],
            expected_cluster_preregistration_hash=context[
                "expected_cluster_preregistration_hash"
            ],
            expected_strata_registration_hash=context[
                "expected_strata_registration_hash"
            ],
            expected_geometry_complete_link_binding_evaluation_hash=context[
                "expected_geometry_complete_link_binding_evaluation_hash"
            ],
            strategy_id=context["strategy_id"],
            variant_id=context["variant_id"],
            lane=context["lane"],
            equity=context["equity"],
            positions=context["positions"],
            proposed_symbol=context["proposed_symbol"],
            proposed_notional=context["proposed_notional"],
            proposed_direction=context["proposed_direction"],
            max_cluster_gross_pct=context["max_cluster_gross_pct"],
            risk_increasing=context["risk_increasing"],
        )
    except Exception:
        return False


def _budget_authority_locked(binding_document: Any, budget_document: Any) -> bool:
    if type(binding_document) is not dict or type(budget_document) is not dict:
        return False
    permissions = binding_document.get("permissions")
    authority = budget_document.get("authority")
    if type(permissions) is not dict or type(authority) is not dict:
        return False
    return bool(
        binding_document.get("current_admission_allowed") is False
        and binding_document.get("current_writer_activation_allowed") is False
        and permissions.get("paper") is False
        and permissions.get("live") is False
        and all(
            authority.get(field) is False
            for field in (
                "runtime_gate_activation_allowed",
                "migration_allowed",
                "writer_allowed",
                "current_admission_allowed",
                "current_pointer_written",
                "paper_authorized",
                "live_order_allowed",
            )
        )
    )


def _preregistration_contexts_from_evaluation(
    uncertainty_gate_context: dict[str, Any],
    budget_evaluation_context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    uncertainty_preregistration = uncertainty_gate_context[
        "uncertainty_preregistration"
    ]
    return (
        {
            "expected_symbols": uncertainty_preregistration.get(
                "expected_symbols"
            ),
            "expected_clusters": uncertainty_preregistration.get(
                "expected_clusters"
            ),
            "expected_windows": uncertainty_preregistration.get(
                "expected_windows"
            ),
            "expected_preregistration_hash": uncertainty_gate_context[
                "expected_preregistration_hash"
            ],
        },
        {
            key: budget_evaluation_context[key]
            for key in _BUDGET_PREREGISTRATION_CONTEXT_KEYS
        },
    )


def _result(
    preregistration: dict[str, Any],
    uncertainty_gate_document: Any,
    budget_binding_evaluation: Any,
    *,
    status: str,
    reason_code: str,
    trace: list[str],
    uncertainty_gate_verified: bool = False,
    budget_verification_attempted: bool = False,
    budget_evaluation_verified: bool = False,
    trusted_budget: dict[str, Any] | None = None,
    risk_increasing: bool | None = None,
) -> dict[str, Any]:
    budget = trusted_budget if type(trusted_budget) is dict else None
    document = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "reason_code": reason_code,
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "preregistration_hash": preregistration["preregistration_hash"],
        "uncertainty_gate_hash": (
            _safe_hash(uncertainty_gate_document, "gate_hash")
            if uncertainty_gate_verified
            else None
        ),
        "uncertainty_gate_status": (
            uncertainty_gate_document.get("status")
            if uncertainty_gate_verified
            else "UNKNOWN"
        ),
        "uncertainty_dependence_edge_count": (
            uncertainty_gate_document.get("dependence_edge_count")
            if uncertainty_gate_verified
            else None
        ),
        "uncertainty_cross_cluster_edge_count": (
            uncertainty_gate_document.get("cross_cluster_dependence_edge_count")
            if uncertainty_gate_verified
            else None
        ),
        "uncertainty_component_count": (
            uncertainty_gate_document.get(
                "derived_conservative_component_count"
            )
            if uncertainty_gate_verified
            else None
        ),
        "geometry_budget_binding_evaluation_hash": (
            _safe_hash(budget_binding_evaluation, "evaluation_hash")
            if budget_evaluation_verified
            else None
        ),
        "effective_budget_v3_hash": (
            _safe_hash(budget, "budget_v3_hash") if budget is not None else None
        ),
        "effective_budget_status": (
            budget.get("status") if budget is not None else None
        ),
        "effective_budget_decision": (
            budget.get("decision") if budget is not None else None
        ),
        "trusted_effective_budget_document": deepcopy(budget),
        "trace": list(trace),
        "facts": {
            "uncertainty_gate_exactly_verified": uncertainty_gate_verified,
            "risk_increasing": risk_increasing,
            "risk_increase_veto_precedes_budget_verification": True,
            "budget_verification_attempted": budget_verification_attempted,
            "budget_evaluation_exactly_verified": budget_evaluation_verified,
            "dynamic_reclustering_performed": False,
            "raw_window_audits_embedded": False,
            "raw_price_or_return_series_embedded": False,
            "runtime_consumer_bound": False,
            "runtime_mutations_performed": False,
            "synthetic_only": True,
            "mounted": False,
            "current_activated": False,
        },
        "blockers": list(_BASE_BLOCKERS),
        "authority": _authority(),
    }
    return _seal(document, "evaluation_hash")


def evaluate_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_v1(
    preregistration: Any,
    uncertainty_gate_document: Any,
    budget_binding_evaluation: Any,
    *,
    expected_preregistration_hash: Any,
    uncertainty_gate_verification_context: Any,
    budget_evaluation_verification_context: Any,
) -> dict[str, Any] | None:
    if type(preregistration) is not dict:
        return None
    if not _exact_context(
        uncertainty_gate_verification_context,
        _UNCERTAINTY_GATE_CONTEXT_KEYS,
    ) or not _exact_context(
        budget_evaluation_verification_context,
        _BUDGET_EVALUATION_CONTEXT_KEYS,
    ):
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="VERIFICATION_CONTEXT_NOT_EXACT",
            trace=[],
        )
    risk_increasing = budget_evaluation_verification_context.get(
        "risk_increasing"
    )
    if type(risk_increasing) is not bool:
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="RISK_DIRECTION_NOT_EXACT",
            trace=[],
        )
    uncertainty_preregistration_context, budget_preregistration_context = (
        _preregistration_contexts_from_evaluation(
            uncertainty_gate_verification_context,
            budget_evaluation_verification_context,
        )
    )
    if not verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1(
        preregistration,
        uncertainty_gate_verification_context["uncertainty_preregistration"],
        budget_evaluation_verification_context[
            "budget_binding_preregistration"
        ],
        expected_preregistration_hash=expected_preregistration_hash,
        uncertainty_preregistration_verification_context=(
            uncertainty_preregistration_context
        ),
        budget_preregistration_verification_context=(
            budget_preregistration_context
        ),
    ):
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="BINDING_PREREGISTRATION_INVALID",
            trace=[],
            risk_increasing=risk_increasing,
        )

    trace: list[str] = []
    if not _uncertainty_gate_exact(
        uncertainty_gate_document,
        uncertainty_gate_verification_context,
    ):
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="UNCERTAINTY_CLUSTER_GATE_INVALID",
            trace=trace,
            risk_increasing=risk_increasing,
        )
    trace.append("UNCERTAINTY_MULTI_WINDOW_CLUSTER_GATE_VERIFIED")
    uncertainty_status = uncertainty_gate_document.get("status")
    if uncertainty_status not in {"PASS", "BLOCK"}:
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="UNCERTAINTY_CLUSTER_GATE_UNKNOWN",
            trace=trace,
            uncertainty_gate_verified=True,
            risk_increasing=risk_increasing,
        )
    if risk_increasing and uncertainty_status == "BLOCK":
        trace.append("RISK_INCREASE_VETOED_BEFORE_BUDGET_VERIFICATION")
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="BLOCK",
            reason_code="CROSS_CLUSTER_DEPENDENCE_REQUIRES_REPREREGISTRATION",
            trace=trace,
            uncertainty_gate_verified=True,
            risk_increasing=True,
        )

    trace.append("GEOMETRY_BOUND_EFFECTIVE_BUDGET_VERIFICATION_ATTEMPTED")
    if not _budget_evaluation_exact(
        budget_binding_evaluation,
        budget_evaluation_verification_context,
    ):
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="GEOMETRY_BOUND_EFFECTIVE_BUDGET_INVALID",
            trace=trace,
            uncertainty_gate_verified=True,
            budget_verification_attempted=True,
            risk_increasing=risk_increasing,
        )
    trace.append("GEOMETRY_BOUND_EFFECTIVE_BUDGET_VERIFIED")
    binding_status = budget_binding_evaluation.get("status")
    if binding_status != "PASS":
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="BLOCK" if binding_status == "BLOCK" else "UNKNOWN",
            reason_code="GEOMETRY_BOUND_EFFECTIVE_BUDGET_DID_NOT_PASS",
            trace=trace,
            uncertainty_gate_verified=True,
            budget_verification_attempted=True,
            budget_evaluation_verified=True,
            risk_increasing=risk_increasing,
        )
    budget = budget_binding_evaluation.get("effective_budget_document")
    if (
        budget_binding_evaluation.get("budget_document_verified") is not True
        or type(budget) is not dict
        or not _budget_authority_locked(budget_binding_evaluation, budget)
    ):
        return _result(
            preregistration,
            uncertainty_gate_document,
            budget_binding_evaluation,
            status="UNKNOWN",
            reason_code="TRUSTED_EFFECTIVE_BUDGET_MISSING_OR_AUTHORITY_INVALID",
            trace=trace,
            uncertainty_gate_verified=True,
            budget_verification_attempted=True,
            budget_evaluation_verified=True,
            risk_increasing=risk_increasing,
        )

    if not risk_increasing:
        if (
            budget.get("status") != "PASS"
            or budget.get("decision") != "RISK_REDUCTION_PATH"
            or budget_binding_evaluation.get("effective_budget_decision")
            != "RISK_REDUCTION_PATH"
        ):
            return _result(
                preregistration,
                uncertainty_gate_document,
                budget_binding_evaluation,
                status="BLOCK",
                reason_code="RISK_REDUCTION_EXCEPTION_NOT_EXACT",
                trace=trace,
                uncertainty_gate_verified=True,
                budget_verification_attempted=True,
                budget_evaluation_verified=True,
                risk_increasing=False,
            )
        trace.append("EXACT_RISK_REDUCTION_PATH_PRESERVED")
        reason_code = (
            "EXACT_RISK_REDUCTION_PRESERVED_UNDER_UNCERTAINTY_BLOCK"
            if uncertainty_status == "BLOCK"
            else "UNCERTAINTY_BOUND_RISK_REDUCTION_BUDGET_VERIFIED"
        )
    else:
        trace.append("RISK_INCREASING_BUDGET_RELEASED_AS_RESEARCH_EVIDENCE")
        reason_code = "UNCERTAINTY_CLUSTER_BOUND_EFFECTIVE_BUDGET_VERIFIED"

    return _result(
        preregistration,
        uncertainty_gate_document,
        budget_binding_evaluation,
        status="PASS",
        reason_code=reason_code,
        trace=trace,
        uncertainty_gate_verified=True,
        budget_verification_attempted=True,
        budget_evaluation_verified=True,
        trusted_budget=budget,
        risk_increasing=risk_increasing,
    )


def verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_evaluation_v1(
    document: Any,
    preregistration: Any,
    uncertainty_gate_document: Any,
    budget_binding_evaluation: Any,
    *,
    expected_evaluation_hash: Any,
    expected_preregistration_hash: Any,
    uncertainty_gate_verification_context: Any,
    budget_evaluation_verification_context: Any,
) -> bool:
    if type(document) is not dict or not _exact_hash(expected_evaluation_hash):
        return False
    expected = evaluate_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_v1(
        preregistration,
        uncertainty_gate_document,
        budget_binding_evaluation,
        expected_preregistration_hash=expected_preregistration_hash,
        uncertainty_gate_verification_context=(
            uncertainty_gate_verification_context
        ),
        budget_evaluation_verification_context=(
            budget_evaluation_verification_context
        ),
    )
    return bool(
        type(expected) is dict
        and document == expected
        and document.get("evaluation_hash") == expected_evaluation_hash
        and compare_digest(expected["evaluation_hash"], expected_evaluation_hash)
    )


__all__ = [
    "ACTIVATION_SEQUENCE",
    "BINDING_CONTRACT_HASH",
    "EFFECTIVE_BUDGET_V3_SOURCE_SHA256",
    "EVALUATION_SCHEMA_VERSION",
    "GEOMETRY_BUDGET_BINDING_SOURCE_SHA256",
    "PREREGISTRATION_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNCERTAINTY_GATE_SOURCE_SHA256",
    "build_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1",
    "evaluate_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_v1",
    "verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_evaluation_v1",
    "verify_strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_preregistration_v1",
]
