"""Unmounted ADR0331-to-presentation-v7 composed binding.

The existing presentation remains unchanged.  This candidate requires an exact
geometry-bound effective-budget evaluation before it will invoke presentation
v7, and it preserves the neutral SOURCE -> GAP -> MATURITY -> PERMISSION axis.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7 as _presentation_v7,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1 as _budget_binding,
)


SCHEMA_VERSION = "strategy-correlation-matrix-geometry-budget-presentation-binding-contract-v1"
PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-presentation-binding-preregistration-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-presentation-binding-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-presentation-binding-v1-unmounted-lock-1"
)

BUDGET_BINDING_MODULE = (
    "exchange_terminal.services.strategy_correlation_matrix_geometry_effective_bet_budget_binding_v1"
)
BUDGET_BINDING_IMPLEMENTATION_SHA256 = (
    "d728150d3ab2d9dd8b998b23d789cb59de2a220274e87b986e4343d5dd9258b3"
)
PRESENTATION_MODULE = (
    "exchange_terminal.services.strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7"
)
PRESENTATION_IMPLEMENTATION_SHA256 = (
    "27bfeacbdcbdfb03009c0dec007274e3c143af1045a8bfe7587ca4629ada8b38"
)
NEUTRAL_AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")
ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_GEOMETRY_BOUND_BUDGET_EVALUATION",
    "DERIVE_BUDGET_V3_CONTEXT_FROM_TRUSTED_CHAIN",
    "BUILD_PRESENTATION_V7",
    "REBUILD_PRESENTATION_V7_WITH_PINNED_BUILDER",
    "VERIFY_PRESENTATION_V7_AND_NEUTRAL_AUTHORITY",
)

_PINNED_PRESENTATION_BUILDER = (
    _presentation_v7.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7
)

_BUDGET_BINDING_CONTEXT_KEYS = frozenset(
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


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return sha256(payload).hexdigest()


def _canonical_external_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _is_exact_hash(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _safe_hash(document: Any, field: str) -> str | None:
    if not isinstance(document, dict):
        return None
    value = document.get(field)
    return value if _is_exact_hash(value) else None


def _self_hash_is_exact(document: Any, field: str, *, external: bool) -> bool:
    stored_hash = _safe_hash(document, field)
    if stored_hash is None:
        return False
    unsigned = deepcopy(document)
    unsigned.pop(field, None)
    rebuilt = (
        _canonical_external_hash(unsigned) if external else _canonical_hash(unsigned)
    )
    return compare_digest(rebuilt, stored_hash)


def _verification_passed(document: Any) -> bool:
    return isinstance(document, dict) and document.get("status") == "PASS"


def _permissions() -> dict[str, bool]:
    return {
        "research_evidence_only": True,
        "current_admission": False,
        "presentation_activation": False,
        "http_registration": False,
        "writer_activation": False,
        "paper": False,
        "live": False,
    }


_CONTRACT_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "activation_sequence": list(ACTIVATION_SEQUENCE),
    "neutral_axis_order": list(NEUTRAL_AXIS_ORDER),
    "budget_binding": {
        "module": BUDGET_BINDING_MODULE,
        "source_sha256": BUDGET_BINDING_IMPLEMENTATION_SHA256,
        "contract_hash": _budget_binding.BINDING_CONTRACT_HASH,
        "static_fingerprint": _budget_binding.STATIC_FINGERPRINT,
        "evaluation_schema_version": _budget_binding.EVALUATION_SCHEMA_VERSION,
    },
    "presentation": {
        "module": PRESENTATION_MODULE,
        "source_sha256": PRESENTATION_IMPLEMENTATION_SHA256,
        "schema_version": _presentation_v7.SCHEMA_VERSION,
        "static_fingerprint": _presentation_v7.STATIC_FINGERPRINT,
        "candidate_builder": (
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7"
        ),
        "exact_rebuilder": (
            "build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7@binding_module_import"
        ),
        "verifier": (
            "verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7"
        ),
    },
    "authority": {
        "mounted": False,
        "presentation_activation_allowed": False,
        "http_registration_allowed": False,
        "current_admission_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
    },
}
BINDING_CONTRACT_HASH = _canonical_hash(_CONTRACT_MANIFEST)


def _budget_binding_preregistration_metadata_is_exact(
    document: Any,
    *,
    expected_preregistration_hash: Any,
) -> bool:
    return bool(
        isinstance(document, dict)
        and _is_exact_hash(expected_preregistration_hash)
        and _safe_hash(document, "preregistration_hash")
        == expected_preregistration_hash
        and _self_hash_is_exact(document, "preregistration_hash", external=False)
        and document.get("schema_version")
        == _budget_binding.PREREGISTRATION_SCHEMA_VERSION
        and document.get("static_fingerprint") == _budget_binding.STATIC_FINGERPRINT
        and document.get("binding_contract_hash")
        == _budget_binding.BINDING_CONTRACT_HASH
        and document.get("status") == "PREREGISTERED_UNMOUNTED"
        and document.get("mounted") is False
        and document.get("current_admission_allowed") is False
        and document.get("current_writer_activation_allowed") is False
    )


def build_strategy_correlation_matrix_geometry_budget_presentation_binding_preregistration_v1(
    budget_binding_preregistration: Any,
    *,
    expected_budget_binding_preregistration_hash: Any,
) -> dict[str, Any] | None:
    if not _budget_binding_preregistration_metadata_is_exact(
        budget_binding_preregistration,
        expected_preregistration_hash=expected_budget_binding_preregistration_hash,
    ):
        return None
    document: dict[str, Any] = {
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "status": "PREREGISTERED_UNMOUNTED",
        "static_fingerprint": STATIC_FINGERPRINT,
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "budget_binding_contract_hash": _budget_binding.BINDING_CONTRACT_HASH,
        "budget_binding_preregistration_hash": (
            expected_budget_binding_preregistration_hash
        ),
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "neutral_axis_order": list(NEUTRAL_AXIS_ORDER),
        "source_bindings": {
            "geometry_budget_binding": {
                "module": BUDGET_BINDING_MODULE,
                "source_sha256": BUDGET_BINDING_IMPLEMENTATION_SHA256,
                "contract_hash": _budget_binding.BINDING_CONTRACT_HASH,
            },
            "presentation_v7": {
                "module": PRESENTATION_MODULE,
                "source_sha256": PRESENTATION_IMPLEMENTATION_SHA256,
            },
        },
        "mounted": False,
        "synthetic_only": True,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": _permissions(),
    }
    document["preregistration_hash"] = _canonical_hash(document)
    return document


def verify_strategy_correlation_matrix_geometry_budget_presentation_binding_preregistration_v1(
    document: Any,
    budget_binding_preregistration: Any,
    *,
    expected_presentation_binding_preregistration_hash: Any,
    expected_budget_binding_preregistration_hash: Any,
) -> bool:
    if not _is_exact_hash(expected_presentation_binding_preregistration_hash):
        return False
    try:
        expected = build_strategy_correlation_matrix_geometry_budget_presentation_binding_preregistration_v1(
            budget_binding_preregistration,
            expected_budget_binding_preregistration_hash=(
                expected_budget_binding_preregistration_hash
            ),
        )
    except Exception:
        return False
    return bool(
        isinstance(document, dict)
        and expected is not None
        and _safe_hash(document, "preregistration_hash")
        == expected_presentation_binding_preregistration_hash
        and compare_digest(
            expected["preregistration_hash"],
            expected_presentation_binding_preregistration_hash,
        )
        and document == expected
    )


def _verify_budget_binding_evaluation(
    document: Any,
    context: Any,
    *,
    expected_evaluation_hash: Any,
) -> bool:
    if (
        not isinstance(context, dict)
        or frozenset(context) != _BUDGET_BINDING_CONTEXT_KEYS
        or context.get("expected_evaluation_hash") != expected_evaluation_hash
    ):
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


def _derived_budget_v3_context(context: dict[str, Any]) -> dict[str, Any] | None:
    upstream = context.get("geometry_complete_link_binding_evaluation")
    if not isinstance(upstream, dict):
        return None
    audit = upstream.get("complete_link_audit")
    gate = upstream.get("complete_link_gate")
    if not isinstance(audit, dict) or not isinstance(gate, dict):
        return None
    return {
        "preregistration": context["cluster_preregistration"],
        "correlation_matrix": context["correlation_matrix"],
        "complete_link_audit": audit,
        "strata_registration": context["strata_registration"],
        "strata_gate": context["strata_gate"],
        "complete_link_gate": gate,
        "equity": context["equity"],
        "positions": context["positions"],
        "proposed_symbol": context["proposed_symbol"],
        "proposed_notional": context["proposed_notional"],
        "proposed_direction": context["proposed_direction"],
        "max_cluster_gross_pct": context["max_cluster_gross_pct"],
        "risk_increasing": context["risk_increasing"],
    }


def _presentation_authority_is_locked(document: Any) -> bool:
    if not isinstance(document, dict) or document.get("axis_order") != list(
        NEUTRAL_AXIS_ORDER
    ):
        return False
    authority = document.get("authority")
    if not isinstance(authority, dict):
        return False
    false_fields = (
        "current_admission_allowed",
        "current_pointer_written",
        "formal_registry_activation_allowed",
        "http_candidate_creation_allowed",
        "live_order_allowed",
        "migration_allowed",
        "paper_authorized",
        "presentation_consumer_activation_allowed",
        "runtime_gate_activation_allowed",
        "writer_allowed",
    )
    return all(authority.get(field) is False for field in false_fields)


def _result(
    *,
    status: str,
    reason_code: str,
    presentation_binding_preregistration: Any,
    budget_binding_evaluation: Any,
    envelope_v6_document: Any,
    trace: list[str],
    presentation_invocation_attempted: bool = False,
    presentation_verified: bool = False,
    trusted_presentation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "status": status,
        "reason_code": reason_code,
        "static_fingerprint": STATIC_FINGERPRINT,
        "binding_contract_hash": BINDING_CONTRACT_HASH,
        "presentation_binding_preregistration_hash": _safe_hash(
            presentation_binding_preregistration, "preregistration_hash"
        ),
        "budget_binding_evaluation_hash": _safe_hash(
            budget_binding_evaluation, "evaluation_hash"
        ),
        "envelope_v6_hash": _safe_hash(envelope_v6_document, "envelope_hash"),
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "axis_order": list(NEUTRAL_AXIS_ORDER),
        "trace": list(trace),
        "presentation_invocation_attempted": presentation_invocation_attempted,
        "presentation_verified": presentation_verified,
        "presentation_status": (
            trusted_presentation.get("status")
            if trusted_presentation is not None
            else None
        ),
        "presentation_decision": (
            trusted_presentation.get("decision")
            if trusted_presentation is not None
            else None
        ),
        "presentation_document": deepcopy(trusted_presentation),
        "mounted": False,
        "synthetic_only": True,
        "current_admission_allowed": False,
        "current_writer_activation_allowed": False,
        "permissions": _permissions(),
    }
    document["evaluation_hash"] = _canonical_hash(document)
    return document


def evaluate_strategy_correlation_matrix_geometry_budget_presentation_binding_v1(
    presentation_binding_preregistration: Any,
    budget_binding_preregistration: Any,
    budget_binding_evaluation: Any,
    envelope_v6_document: Any,
    *,
    expected_presentation_binding_preregistration_hash: Any,
    expected_budget_binding_preregistration_hash: Any,
    expected_budget_binding_evaluation_hash: Any,
    budget_binding_verification_context: Any,
    envelope_v6_verification_context: Any,
) -> dict[str, Any]:
    trace: list[str] = []
    common = {
        "presentation_binding_preregistration": (
            presentation_binding_preregistration
        ),
        "budget_binding_evaluation": budget_binding_evaluation,
        "envelope_v6_document": envelope_v6_document,
        "trace": trace,
    }
    if not verify_strategy_correlation_matrix_geometry_budget_presentation_binding_preregistration_v1(
        presentation_binding_preregistration,
        budget_binding_preregistration,
        expected_presentation_binding_preregistration_hash=(
            expected_presentation_binding_preregistration_hash
        ),
        expected_budget_binding_preregistration_hash=(
            expected_budget_binding_preregistration_hash
        ),
    ):
        return _result(
            status="UNKNOWN",
            reason_code="PRESENTATION_BINDING_PREREGISTRATION_INVALID",
            **common,
        )

    if not _is_exact_hash(expected_budget_binding_evaluation_hash) or not (
        _verify_budget_binding_evaluation(
            budget_binding_evaluation,
            budget_binding_verification_context,
            expected_evaluation_hash=expected_budget_binding_evaluation_hash,
        )
    ):
        return _result(
            status="UNKNOWN",
            reason_code="GEOMETRY_BOUND_BUDGET_EVALUATION_INVALID",
            **common,
        )
    trace.append("GEOMETRY_BOUND_BUDGET_EVALUATION_VERIFIED")

    if budget_binding_evaluation.get("status") != "PASS":
        return _result(
            status=(
                "BLOCK"
                if budget_binding_evaluation.get("status") == "BLOCK"
                else "UNKNOWN"
            ),
            reason_code="GEOMETRY_BOUND_BUDGET_EVALUATION_DID_NOT_PASS",
            **common,
        )
    budget_document = budget_binding_evaluation.get("effective_budget_document")
    if (
        budget_binding_evaluation.get("budget_document_verified") is not True
        or not isinstance(budget_document, dict)
    ):
        return _result(
            status="UNKNOWN",
            reason_code="TRUSTED_EFFECTIVE_BUDGET_DOCUMENT_MISSING",
            **common,
        )

    budget_v3_context = _derived_budget_v3_context(
        budget_binding_verification_context
    )
    if budget_v3_context is None:
        return _result(
            status="UNKNOWN",
            reason_code="BUDGET_V3_VERIFICATION_CONTEXT_INVALID",
            **common,
        )
    trace.append("BUDGET_V3_CONTEXT_DERIVED_FROM_TRUSTED_CHAIN")

    trace.append("PRESENTATION_V7_INVOCATION_ATTEMPTED")
    try:
        presentation = _presentation_v7.build_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7(
            envelope_v6_document,
            budget_document,
            envelope_v6_verification_context=envelope_v6_verification_context,
            budget_v3_verification_context=budget_v3_context,
        )
    except Exception:
        return _result(
            status="UNKNOWN",
            reason_code="PRESENTATION_V7_CONSUMER_EXCEPTION",
            presentation_invocation_attempted=True,
            **common,
        )
    if not isinstance(presentation, dict):
        return _result(
            status="UNKNOWN",
            reason_code="PRESENTATION_V7_DOCUMENT_INVALID",
            presentation_invocation_attempted=True,
            **common,
        )

    try:
        expected_presentation = _PINNED_PRESENTATION_BUILDER(
            envelope_v6_document,
            budget_document,
            envelope_v6_verification_context=envelope_v6_verification_context,
            budget_v3_verification_context=budget_v3_context,
        )
    except Exception:
        return _result(
            status="UNKNOWN",
            reason_code="PRESENTATION_V7_EXACT_REBUILD_EXCEPTION",
            presentation_invocation_attempted=True,
            **common,
        )
    if (
        not _self_hash_is_exact(
            presentation, "presentation_v7_hash", external=True
        )
        or presentation != expected_presentation
    ):
        return _result(
            status="UNKNOWN",
            reason_code="PRESENTATION_V7_DOCUMENT_INVALID",
            presentation_invocation_attempted=True,
            **common,
        )

    try:
        verification = _presentation_v7.verify_strategy_correlation_cluster_portfolio_risk_stratified_presentation_v7(
            presentation,
            envelope_v6_document,
            budget_document,
            envelope_v6_verification_context=envelope_v6_verification_context,
            budget_v3_verification_context=budget_v3_context,
        )
    except Exception:
        verification = None
    if not _verification_passed(verification):
        return _result(
            status="UNKNOWN",
            reason_code="PRESENTATION_V7_VERIFICATION_FAILED",
            presentation_invocation_attempted=True,
            **common,
        )
    trace.append("PRESENTATION_V7_VERIFIED")

    if not _presentation_authority_is_locked(presentation):
        return _result(
            status="UNKNOWN",
            reason_code="PRESENTATION_V7_NEUTRAL_AUTHORITY_INVARIANT_FAILED",
            presentation_invocation_attempted=True,
            **common,
        )

    return _result(
        status="PASS",
        reason_code="GEOMETRY_BOUND_BUDGET_PRESENTATION_VERIFIED",
        presentation_invocation_attempted=True,
        presentation_verified=True,
        trusted_presentation=presentation,
        **common,
    )


def verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1(
    document: Any,
    presentation_binding_preregistration: Any,
    budget_binding_preregistration: Any,
    budget_binding_evaluation: Any,
    envelope_v6_document: Any,
    *,
    expected_evaluation_hash: Any,
    expected_presentation_binding_preregistration_hash: Any,
    expected_budget_binding_preregistration_hash: Any,
    expected_budget_binding_evaluation_hash: Any,
    budget_binding_verification_context: Any,
    envelope_v6_verification_context: Any,
) -> bool:
    if not _is_exact_hash(expected_evaluation_hash):
        return False
    try:
        expected = evaluate_strategy_correlation_matrix_geometry_budget_presentation_binding_v1(
            presentation_binding_preregistration,
            budget_binding_preregistration,
            budget_binding_evaluation,
            envelope_v6_document,
            expected_presentation_binding_preregistration_hash=(
                expected_presentation_binding_preregistration_hash
            ),
            expected_budget_binding_preregistration_hash=(
                expected_budget_binding_preregistration_hash
            ),
            expected_budget_binding_evaluation_hash=(
                expected_budget_binding_evaluation_hash
            ),
            budget_binding_verification_context=(
                budget_binding_verification_context
            ),
            envelope_v6_verification_context=(
                envelope_v6_verification_context
            ),
        )
    except Exception:
        return False
    return bool(
        isinstance(document, dict)
        and _safe_hash(document, "evaluation_hash") == expected_evaluation_hash
        and compare_digest(expected["evaluation_hash"], expected_evaluation_hash)
        and document == expected
    )
