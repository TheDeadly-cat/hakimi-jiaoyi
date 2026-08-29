"""Unmounted ADR0332-bound multi-window presentation wrapper v9."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from hmac import compare_digest
import json
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7 as _adapter_v7,
)
from exchange_terminal.services import (
    strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8 as _multi_window_v8,
)
from exchange_terminal.services import (
    strategy_correlation_matrix_geometry_budget_presentation_binding_v1 as _presentation_binding,
)


SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-binding-v9"
)
VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-matrix-geometry-budget-multi-window-presentation-binding-v9-verification-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-matrix-geometry-budget-multi-window-presentation-v9-unmounted-lock-1"
)
PRESENTATION_BINDING_IMPLEMENTATION_SHA256 = (
    "e482206ff0e4a6e805e6f7318305135c8a291c4f9a1065ca2975b9ddb6093113"
)
ADAPTER_V7_IMPLEMENTATION_SHA256 = (
    "09ecd921823260df4e8fda708f3c276d40fccd22c390b0ef7f920f9d9fc52f3e"
)
MULTI_WINDOW_V8_IMPLEMENTATION_SHA256 = (
    "f2720ff7b2b32e7ffdf4c83502b1fa65f83ceb3ee8806dae94b0aaf71fd8ba6b"
)
NEUTRAL_AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

_PRESENTATION_CONTEXT_KEYS = frozenset(
    {
        "presentation_binding_preregistration",
        "budget_binding_preregistration",
        "budget_binding_evaluation",
        "envelope_v6_document",
        "expected_evaluation_hash",
        "expected_presentation_binding_preregistration_hash",
        "expected_budget_binding_preregistration_hash",
        "expected_budget_binding_evaluation_hash",
        "budget_binding_verification_context",
        "envelope_v6_verification_context",
    }
)
_ADAPTER_CONTEXT_KEYS = frozenset(
    {
        "stability_gate_v2_document",
        "stability_gate_v2_verification_context",
        "risk_increasing",
    }
)

_PINNED_ADAPTER_EVALUATOR = (
    _adapter_v7.evaluate_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7
)
_PINNED_MULTI_WINDOW_BUILDER = (
    _multi_window_v8.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8
)


def _canonical_hash(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


def _canonical_external_hash(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


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


def _self_hash_is_exact(document: Any, field: str) -> bool:
    stored = _safe_hash(document, field)
    if stored is None:
        return False
    unsigned = deepcopy(document)
    unsigned.pop(field, None)
    return compare_digest(_canonical_external_hash(unsigned), stored)


def _verification_passed(document: Any) -> bool:
    return isinstance(document, dict) and document.get("status") == "PASS"


_CONTRACT_MANIFEST = {
    "schema_version": SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "neutral_axis_order": list(NEUTRAL_AXIS_ORDER),
    "presentation_binding": {
        "source_sha256": PRESENTATION_BINDING_IMPLEMENTATION_SHA256,
        "contract_hash": _presentation_binding.BINDING_CONTRACT_HASH,
        "static_fingerprint": _presentation_binding.STATIC_FINGERPRINT,
    },
    "adapter_v7": {
        "source_sha256": ADAPTER_V7_IMPLEMENTATION_SHA256,
        "schema_version": _adapter_v7.SCHEMA_VERSION,
        "static_fingerprint": _adapter_v7.STATIC_FINGERPRINT,
        "exact_rebuilder": "adapter_v7_evaluator@v9_import",
    },
    "multi_window_v8": {
        "source_sha256": MULTI_WINDOW_V8_IMPLEMENTATION_SHA256,
        "schema_version": _multi_window_v8.SCHEMA_VERSION,
        "static_fingerprint": _multi_window_v8.STATIC_FINGERPRINT,
        "exact_rebuilder": "multi_window_v8_builder@v9_import",
    },
    "authority": {
        "mounted": False,
        "ui_mounted": False,
        "http_candidate_registered": False,
        "current_admission_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    },
}
CONTRACT_HASH = _canonical_hash(_CONTRACT_MANIFEST)


def _verify_presentation_binding(document: Any, context: Any) -> bool:
    if not isinstance(context, dict) or frozenset(context) != _PRESENTATION_CONTEXT_KEYS:
        return False
    try:
        return _presentation_binding.verify_strategy_correlation_matrix_geometry_budget_presentation_binding_evaluation_v1(
            document,
            context["presentation_binding_preregistration"],
            context["budget_binding_preregistration"],
            context["budget_binding_evaluation"],
            context["envelope_v6_document"],
            expected_evaluation_hash=context["expected_evaluation_hash"],
            expected_presentation_binding_preregistration_hash=context[
                "expected_presentation_binding_preregistration_hash"
            ],
            expected_budget_binding_preregistration_hash=context[
                "expected_budget_binding_preregistration_hash"
            ],
            expected_budget_binding_evaluation_hash=context[
                "expected_budget_binding_evaluation_hash"
            ],
            budget_binding_verification_context=context[
                "budget_binding_verification_context"
            ],
            envelope_v6_verification_context=context[
                "envelope_v6_verification_context"
            ],
        )
    except Exception:
        return False


def _budget_document_and_context(
    presentation_context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    budget_binding_evaluation = presentation_context.get("budget_binding_evaluation")
    budget_binding_context = presentation_context.get(
        "budget_binding_verification_context"
    )
    if not isinstance(budget_binding_evaluation, dict) or not isinstance(
        budget_binding_context, dict
    ):
        return None
    budget = budget_binding_evaluation.get("effective_budget_document")
    budget_context = _presentation_binding._derived_budget_v3_context(
        budget_binding_context
    )
    if not isinstance(budget, dict) or budget_context is None:
        return None
    return budget, budget_context


def _presentation_v7_context(
    presentation_context: dict[str, Any],
    budget: dict[str, Any],
    budget_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "envelope_v6_document": presentation_context["envelope_v6_document"],
        "budget_v3_document": budget,
        "envelope_v6_verification_context": presentation_context[
            "envelope_v6_verification_context"
        ],
        "budget_v3_verification_context": budget_context,
    }


def _adapter_v7_context(
    adapter_context: dict[str, Any],
    budget: dict[str, Any],
    budget_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "anchor_budget_v3_document": budget,
        "anchor_budget_v3_verification_context": budget_context,
        "stability_gate_v2_document": adapter_context[
            "stability_gate_v2_document"
        ],
        "stability_gate_v2_verification_context": adapter_context[
            "stability_gate_v2_verification_context"
        ],
        "risk_increasing": adapter_context["risk_increasing"],
    }


def _authority_is_locked(document: Any) -> bool:
    if (
        not isinstance(document, dict)
        or document.get("axis_order") != list(NEUTRAL_AXIS_ORDER)
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
        "paper_authorized",
        "presentation_consumer_activation_allowed",
        "runtime_gate_activation_allowed",
        "writer_allowed",
    )
    facts = document.get("facts")
    return bool(
        all(authority.get(field) is False for field in false_fields)
        and isinstance(facts, dict)
        and facts.get("ui_mounted") is False
        and facts.get("http_candidate_registered") is False
        and facts.get("runtime_consumer_bound") is False
    )


def _result(
    *,
    status: str,
    reason_code: str,
    presentation_binding_evaluation: Any,
    adapter_v7_document: Any,
    invocation_attempted: bool = False,
    verified: bool = False,
    trusted_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reason_code": reason_code,
        "static_fingerprint": STATIC_FINGERPRINT,
        "contract_hash": CONTRACT_HASH,
        "axis_order": list(NEUTRAL_AXIS_ORDER),
        "presentation_binding_evaluation_hash": _safe_hash(
            presentation_binding_evaluation, "evaluation_hash"
        ),
        "adapter_v7_hash": _safe_hash(adapter_v7_document, "adapter_v7_hash"),
        "multi_window_v8_hash": _safe_hash(
            trusted_document, "presentation_v8_hash"
        ),
        "multi_window_invocation_attempted": invocation_attempted,
        "multi_window_verified": verified,
        "multi_window_status": (
            trusted_document.get("status") if trusted_document else None
        ),
        "multi_window_decision": (
            trusted_document.get("decision") if trusted_document else None
        ),
        "multi_window_document": deepcopy(trusted_document),
        "mounted": False,
        "synthetic_only": True,
        "facts": {
            "ui_mounted": False,
            "http_candidate_registered": False,
            "runtime_consumer_bound": False,
        },
        "authority": {
            "current_admission_allowed": False,
            "writer_allowed": False,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    document["evaluation_hash"] = _canonical_hash(document)
    return document


def evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
    presentation_binding_evaluation: Any,
    adapter_v7_document: Any,
    *,
    expected_presentation_binding_evaluation_hash: Any,
    expected_adapter_v7_hash: Any,
    presentation_binding_verification_context: Any,
    adapter_v7_verification_context: Any,
) -> dict[str, Any]:
    common = {
        "presentation_binding_evaluation": presentation_binding_evaluation,
        "adapter_v7_document": adapter_v7_document,
    }
    if (
        not _is_exact_hash(expected_presentation_binding_evaluation_hash)
        or _safe_hash(presentation_binding_evaluation, "evaluation_hash")
        != expected_presentation_binding_evaluation_hash
        or not isinstance(presentation_binding_verification_context, dict)
        or presentation_binding_verification_context.get("expected_evaluation_hash")
        != expected_presentation_binding_evaluation_hash
        or not _verify_presentation_binding(
            presentation_binding_evaluation,
            presentation_binding_verification_context,
        )
    ):
        return _result(
            status="UNKNOWN",
            reason_code="PRESENTATION_BINDING_EVALUATION_INVALID",
            **common,
        )
    if presentation_binding_evaluation.get("status") != "PASS":
        return _result(
            status=(
                "BLOCK"
                if presentation_binding_evaluation.get("status") == "BLOCK"
                else "UNKNOWN"
            ),
            reason_code="PRESENTATION_BINDING_EVALUATION_DID_NOT_PASS",
            **common,
        )
    presentation = presentation_binding_evaluation.get("presentation_document")
    if (
        presentation_binding_evaluation.get("presentation_verified") is not True
        or not isinstance(presentation, dict)
    ):
        return _result(
            status="UNKNOWN",
            reason_code="TRUSTED_PRESENTATION_V7_MISSING",
            **common,
        )
    if (
        not isinstance(adapter_v7_verification_context, dict)
        or frozenset(adapter_v7_verification_context) != _ADAPTER_CONTEXT_KEYS
        or not _is_exact_hash(expected_adapter_v7_hash)
        or _safe_hash(adapter_v7_document, "adapter_v7_hash")
        != expected_adapter_v7_hash
    ):
        return _result(
            status="UNKNOWN",
            reason_code="ADAPTER_V7_INPUT_INVALID",
            **common,
        )
    budget_pair = _budget_document_and_context(
        presentation_binding_verification_context
    )
    if budget_pair is None:
        return _result(
            status="UNKNOWN",
            reason_code="TRUSTED_BUDGET_CONTEXT_MISSING",
            **common,
        )
    budget, budget_context = budget_pair
    try:
        expected_adapter = _PINNED_ADAPTER_EVALUATOR(
            budget,
            adapter_v7_verification_context["stability_gate_v2_document"],
            anchor_budget_v3_verification_context=budget_context,
            stability_gate_v2_verification_context=adapter_v7_verification_context[
                "stability_gate_v2_verification_context"
            ],
            risk_increasing=adapter_v7_verification_context["risk_increasing"],
        )
    except Exception:
        return _result(
            status="UNKNOWN",
            reason_code="ADAPTER_V7_EXACT_REBUILD_EXCEPTION",
            **common,
        )
    if (
        not _self_hash_is_exact(adapter_v7_document, "adapter_v7_hash")
        or adapter_v7_document != expected_adapter
    ):
        return _result(
            status="UNKNOWN",
            reason_code="ADAPTER_V7_DOCUMENT_INVALID",
            **common,
        )
    try:
        adapter_verification = _adapter_v7.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_adapter_v7(
            adapter_v7_document,
            budget,
            adapter_v7_verification_context["stability_gate_v2_document"],
            anchor_budget_v3_verification_context=budget_context,
            stability_gate_v2_verification_context=adapter_v7_verification_context[
                "stability_gate_v2_verification_context"
            ],
            risk_increasing=adapter_v7_verification_context["risk_increasing"],
        )
    except Exception:
        adapter_verification = None
    if not _verification_passed(adapter_verification):
        return _result(
            status="UNKNOWN",
            reason_code="ADAPTER_V7_VERIFICATION_FAILED",
            **common,
        )

    presentation_context = _presentation_v7_context(
        presentation_binding_verification_context,
        budget,
        budget_context,
    )
    adapter_context = _adapter_v7_context(
        adapter_v7_verification_context,
        budget,
        budget_context,
    )
    try:
        candidate = _multi_window_v8.build_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8(
            presentation,
            adapter_v7_document,
            presentation_v7_verification_context=presentation_context,
            adapter_v7_verification_context=adapter_context,
        )
    except Exception:
        return _result(
            status="UNKNOWN",
            reason_code="MULTI_WINDOW_V8_CONSUMER_EXCEPTION",
            invocation_attempted=True,
            **common,
        )
    try:
        expected = _PINNED_MULTI_WINDOW_BUILDER(
            presentation,
            adapter_v7_document,
            presentation_v7_verification_context=presentation_context,
            adapter_v7_verification_context=adapter_context,
        )
    except Exception:
        return _result(
            status="UNKNOWN",
            reason_code="MULTI_WINDOW_V8_EXACT_REBUILD_EXCEPTION",
            invocation_attempted=True,
            **common,
        )
    if (
        not _self_hash_is_exact(candidate, "presentation_v8_hash")
        or candidate != expected
    ):
        return _result(
            status="UNKNOWN",
            reason_code="MULTI_WINDOW_V8_DOCUMENT_INVALID",
            invocation_attempted=True,
            **common,
        )
    try:
        verification = _multi_window_v8.verify_strategy_correlation_cluster_portfolio_risk_stratified_multi_window_presentation_v8(
            candidate,
            presentation,
            adapter_v7_document,
            presentation_v7_verification_context=presentation_context,
            adapter_v7_verification_context=adapter_context,
        )
    except Exception:
        verification = None
    if not _verification_passed(verification) or not _authority_is_locked(candidate):
        return _result(
            status="UNKNOWN",
            reason_code="MULTI_WINDOW_V8_VERIFICATION_OR_AUTHORITY_INVALID",
            invocation_attempted=True,
            **common,
        )
    return _result(
        status="PASS",
        reason_code="GEOMETRY_BOUND_MULTI_WINDOW_PRESENTATION_VERIFIED",
        invocation_attempted=True,
        verified=True,
        trusted_document=candidate,
        **common,
    )


def verify_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
    document: Any,
    presentation_binding_evaluation: Any,
    adapter_v7_document: Any,
    *,
    expected_evaluation_hash: Any,
    expected_presentation_binding_evaluation_hash: Any,
    expected_adapter_v7_hash: Any,
    presentation_binding_verification_context: Any,
    adapter_v7_verification_context: Any,
) -> dict[str, Any]:
    try:
        expected = evaluate_strategy_correlation_matrix_geometry_budget_multi_window_presentation_binding_v9(
            presentation_binding_evaluation,
            adapter_v7_document,
            expected_presentation_binding_evaluation_hash=(
                expected_presentation_binding_evaluation_hash
            ),
            expected_adapter_v7_hash=expected_adapter_v7_hash,
            presentation_binding_verification_context=(
                presentation_binding_verification_context
            ),
            adapter_v7_verification_context=adapter_v7_verification_context,
        )
    except Exception:
        expected = None
    valid = bool(
        _is_exact_hash(expected_evaluation_hash)
        and isinstance(document, dict)
        and isinstance(expected, dict)
        and _safe_hash(document, "evaluation_hash") == expected_evaluation_hash
        and compare_digest(expected["evaluation_hash"], expected_evaluation_hash)
        and document == expected
    )
    return {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if valid else "BLOCK",
        "evaluation_hash": expected_evaluation_hash if valid else None,
        "current_admission_allowed": False,
        "writer_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
