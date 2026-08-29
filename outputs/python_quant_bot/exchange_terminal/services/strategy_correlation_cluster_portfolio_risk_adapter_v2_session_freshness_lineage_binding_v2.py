"""Uncertainty-projection-aware adapter/freshness lineage binding v2."""

from __future__ import annotations

from typing import Any

from . import (
    strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1
    as binding_v1,
)
from .strategy_correlation_cluster_gate import build_correlation_matrix_contract
from .strategy_correlation_uncertainty_audit import (
    build_strategy_correlation_uncertainty_audit,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


BINDING_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-adapter-v2-"
    "session-freshness-lineage-binding-v2"
)
BINDING_VERIFICATION_SCHEMA_VERSION = f"{BINDING_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = (
    "20260822-portfolio-risk-adapter-freshness-uncertainty-lineage-lock-1"
)

_ADAPTER_V2_CONTEXT_KEYS = {
    "adapter_v1_document",
    "temporal_stability_gate",
    "adapter_v1_verification_context",
    "temporal_stability_verification_context",
}
_ADAPTER_V1_CONTEXT_KEYS = {
    "preregistration",
    "cluster_correlation_matrix",
    "complete_link_audit",
    "equity",
    "positions",
    "proposed_symbol",
    "proposed_notional",
    "proposed_direction",
    "proposed_cluster",
    "risk_increasing",
    "legacy_correlations",
    "regime",
    "legacy_limits",
    "max_cluster_gross_pct",
}
_FRESHNESS_CONTEXT_KEYS = {
    "registration",
    "registration_inputs",
    "trusted_clock_attestation",
    "expected_trusted_clock_attestation_hash",
}
_REGISTRATION_INPUT_KEYS = {
    "native_cutoff_manifest",
    "native_cutoff_context",
    "expected_native_cutoff_manifest_hash",
    "max_completed_session_lag",
    "declared_at_utc",
}
_NATIVE_CONTEXT_KEYS = {
    "completed_price_input",
    "matrix_replay",
    "derivation_receipt",
    "composition_document",
    "composition_context",
    "expected_observation_cutoff_utc",
}
_LEGACY_CONTEXT_KEYS = {
    "legacy_correlation_matrix",
    "completed_price_input",
    "matrix_replay",
    "derivation_receipt",
    "composition_document",
    "composition_context",
    "dataset_attestation_verification",
    "dataset_attestation_registration",
    "provider_dataset_public_key_base64",
    "dataset_attestation_receipt",
    "expected_registration_hash",
    "expected_attestation_hash",
}
_V1_CHECK_NAMES = {
    "adapter_v2_exact_verification",
    "session_freshness_exact_verification",
    "legacy_matrix_binding_exact_verification",
    "adapter_native_preregistration_identity",
    "adapter_native_pairwise_matrix_identity",
    "adapter_legacy_matrix_projection_identity",
    "freshness_legacy_native_document_chain",
    "native_manifest_registration_evaluation_hash_chain",
    "native_cutoff_date_continuity",
    "public_source_hash_projection",
    "external_trust_and_authority_not_promoted",
}
_V1_REPLACED_CHECKS = {
    "adapter_native_pairwise_matrix_identity",
    "public_source_hash_projection",
}


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _exact_dict(value: Any, keys: set[str]) -> dict[str, Any]:
    return value if type(value) is dict and set(value) == keys else {}


def _text_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _check(name: str, ok: bool) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "blocking": True}


def _project_uncertainty_matrix(
    matrix_replay: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    replay = _dict(matrix_replay)
    preregistration = _dict(replay.get("preregistration"))
    try:
        audit = build_strategy_correlation_uncertainty_audit(replay)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return {}, {}
    correlations: dict[tuple[str, str], int | float] = {}
    overlaps: dict[tuple[str, str], int] = {}
    for item in _list(audit.get("pairs")):
        pair = _dict(item)
        left = pair.get("left_symbol")
        right = pair.get("right_symbol")
        correlation = pair.get("correlation")
        overlap = pair.get("overlap_observations")
        if (
            type(left) is not str
            or type(right) is not str
            or type(correlation) not in (int, float)
            or type(overlap) is not int
        ):
            return {}, {}
        key = (left, right)
        correlations[key] = correlation
        overlaps[key] = overlap
    symbols = preregistration.get("symbols")
    if type(symbols) is not list or not correlations:
        return {}, {}
    try:
        matrix = build_correlation_matrix_contract(
            symbols,
            correlations,
            overlap_observations=overlaps,
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return {}, {}
    return audit if type(audit) is dict else {}, matrix if type(matrix) is dict else {}


def build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2(
    adapter_v2_document: Any,
    freshness_evaluation: Any,
    legacy_matrix_binding: Any,
    *,
    adapter_v2_verification_context: Any,
    freshness_verification_context: Any,
    legacy_matrix_binding_verification_context: Any,
) -> dict[str, Any]:
    predecessor = binding_v1.build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1(
        adapter_v2_document,
        freshness_evaluation,
        legacy_matrix_binding,
        adapter_v2_verification_context=adapter_v2_verification_context,
        freshness_verification_context=freshness_verification_context,
        legacy_matrix_binding_verification_context=(
            legacy_matrix_binding_verification_context
        ),
    )
    predecessor_checks = {
        item.get("name"): item.get("ok")
        for item in _list(_dict(predecessor).get("checks"))
        if type(item) is dict
    }
    predecessor_blockers = set(_list(_dict(predecessor).get("blockers")))
    predecessor_diagnostics_compatible = bool(
        predecessor.get("schema_version") == binding_v1.BINDING_SCHEMA_VERSION
        and predecessor.get("static_fingerprint") == binding_v1.STATIC_FINGERPRINT
        and strict_sha256(predecessor.get("lineage_binding_hash"))
        and set(predecessor_checks) == _V1_CHECK_NAMES
        and all(
            predecessor_checks.get(name) is True
            for name in _V1_CHECK_NAMES - _V1_REPLACED_CHECKS
        )
        and predecessor_blockers.issubset(_V1_REPLACED_CHECKS)
        and (
            predecessor.get("status") == "PASS"
            or (
                predecessor.get("status") == "BLOCK"
                and bool(predecessor_blockers)
            )
        )
    )

    adapter_context = _exact_dict(
        adapter_v2_verification_context, _ADAPTER_V2_CONTEXT_KEYS
    )
    adapter_v1_context = _exact_dict(
        adapter_context.get("adapter_v1_verification_context"),
        _ADAPTER_V1_CONTEXT_KEYS,
    )
    temporal_context = _dict(
        adapter_context.get("temporal_stability_verification_context")
    )
    freshness_context = _exact_dict(
        freshness_verification_context, _FRESHNESS_CONTEXT_KEYS
    )
    registration_inputs = _exact_dict(
        freshness_context.get("registration_inputs"), _REGISTRATION_INPUT_KEYS
    )
    native_context = _exact_dict(
        registration_inputs.get("native_cutoff_context"), _NATIVE_CONTEXT_KEYS
    )
    legacy_context = _exact_dict(
        legacy_matrix_binding_verification_context, _LEGACY_CONTEXT_KEYS
    )
    matrix_replay = _dict(native_context.get("matrix_replay"))
    native_preregistration = _dict(matrix_replay.get("preregistration"))
    native_pairwise_matrix = _dict(matrix_replay.get("correlation_matrix"))

    rebuilt_uncertainty, projected_matrix = _project_uncertainty_matrix(matrix_replay)
    uncertainty_exact = bool(
        rebuilt_uncertainty
        and strict_sha256(rebuilt_uncertainty.get("audit_hash"))
    )
    temporal_uncertainty_identity = bool(
        uncertainty_exact
        and strict_json_contract_equal(
            temporal_context.get("source_uncertainty_audit"),
            rebuilt_uncertainty,
        )
    )
    projected_matrix_identity = bool(
        projected_matrix
        and strict_json_contract_equal(
            adapter_v1_context.get("cluster_correlation_matrix"),
            projected_matrix,
        )
    )

    adapter_document = _dict(adapter_v2_document)
    adapter_source = _dict(adapter_document.get("source"))
    legacy_document = _dict(legacy_matrix_binding)
    legacy_source = _dict(legacy_document.get("source"))
    freshness_document = _dict(freshness_evaluation)
    freshness_source = _dict(freshness_document.get("source"))
    registration = _dict(freshness_context.get("registration"))
    registration_source = _dict(registration.get("source"))
    native_manifest = _dict(registration_inputs.get("native_cutoff_manifest"))
    completed_input = _dict(native_context.get("completed_price_input"))
    legacy_matrix = _dict(legacy_context.get("legacy_correlation_matrix"))

    corrected_source_hash_projection = bool(
        strict_sha256(native_preregistration.get("preregistration_hash"))
        and adapter_source.get("preregistration_hash")
        == native_preregistration.get("preregistration_hash")
        and strict_sha256(projected_matrix.get("matrix_hash"))
        and adapter_source.get("correlation_matrix_hash")
        == projected_matrix.get("matrix_hash")
        and strict_sha256(native_pairwise_matrix.get("matrix_hash"))
        and strict_sha256(rebuilt_uncertainty.get("audit_hash"))
        and strict_sha256(legacy_matrix.get("matrix_hash"))
        and legacy_source.get("legacy_matrix_hash") == legacy_matrix.get("matrix_hash")
        and legacy_source.get("preregistration_hash")
        == native_preregistration.get("preregistration_hash")
        and legacy_source.get("completed_price_input_hash")
        == completed_input.get("input_hash")
        and legacy_source.get("matrix_replay_hash") == matrix_replay.get("replay_hash")
        and strict_sha256(native_manifest.get("manifest_hash"))
        and registration_inputs.get("expected_native_cutoff_manifest_hash")
        == native_manifest.get("manifest_hash")
        and registration_source.get("native_cutoff_manifest_hash")
        == native_manifest.get("manifest_hash")
        and freshness_source.get("native_cutoff_manifest_hash")
        == native_manifest.get("manifest_hash")
        and strict_sha256(registration.get("registration_hash"))
        and freshness_source.get("registration_hash")
        == registration.get("registration_hash")
    )

    checks = [
        _check("binding_v1_predecessor_diagnostics_compatible", predecessor_diagnostics_compatible),
        _check("native_uncertainty_audit_exact_rebuild", uncertainty_exact),
        _check("adapter_temporal_uncertainty_audit_identity", temporal_uncertainty_identity),
        _check("adapter_uncertainty_matrix_projection_identity", projected_matrix_identity),
        _check("corrected_public_source_hash_projection", corrected_source_hash_projection),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    passed = not blockers
    source_available = passed
    predecessor_states = _dict(predecessor.get("component_states"))
    expected_cutoff = native_context.get("expected_observation_cutoff_utc")

    document: dict[str, Any] = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if passed else "BLOCK",
        "decision": (
            "EXACT_NATIVE_UNCERTAINTY_PROJECTION_LINEAGE_BOUND_"
            "COMPONENT_DECISIONS_NOT_PROMOTED_EXTERNAL_TRUST_UNPROVEN"
            if passed
            else "BLOCKED_ADAPTER_FRESHNESS_UNCERTAINTY_LINEAGE_BINDING"
        ),
        "source": {
            "binding_v1_assessment_hash": (
                _text_or_none(predecessor.get("lineage_binding_hash"))
                if source_available
                else None
            ),
            "adapter_v2_hash": (
                _text_or_none(adapter_document.get("adapter_hash"))
                if source_available
                else None
            ),
            "freshness_evaluation_hash": (
                _text_or_none(freshness_document.get("evaluation_hash"))
                if source_available
                else None
            ),
            "legacy_matrix_binding_hash": (
                _text_or_none(legacy_document.get("binding_hash"))
                if source_available
                else None
            ),
            "native_cutoff_manifest_hash": (
                _text_or_none(native_manifest.get("manifest_hash"))
                if source_available
                else None
            ),
            "freshness_registration_hash": (
                _text_or_none(registration.get("registration_hash"))
                if source_available
                else None
            ),
            "completed_price_input_hash": (
                _text_or_none(completed_input.get("input_hash"))
                if source_available
                else None
            ),
            "matrix_replay_hash": (
                _text_or_none(matrix_replay.get("replay_hash"))
                if source_available
                else None
            ),
            "preregistration_hash": (
                _text_or_none(native_preregistration.get("preregistration_hash"))
                if source_available
                else None
            ),
            "native_pairwise_matrix_hash": (
                _text_or_none(native_pairwise_matrix.get("matrix_hash"))
                if source_available
                else None
            ),
            "native_uncertainty_audit_hash": (
                _text_or_none(rebuilt_uncertainty.get("audit_hash"))
                if source_available
                else None
            ),
            "adapter_projected_matrix_hash": (
                _text_or_none(projected_matrix.get("matrix_hash"))
                if source_available
                else None
            ),
            "legacy_matrix_hash": (
                _text_or_none(legacy_matrix.get("matrix_hash"))
                if source_available
                else None
            ),
            "observation_cutoff_utc": (
                expected_cutoff
                if source_available and type(expected_cutoff) is str
                else None
            ),
        },
        "component_states": {
            key: predecessor_states.get(key, "UNKNOWN")
            for key in (
                "adapter_v2_status",
                "adapter_v2_decision",
                "session_freshness_status",
                "session_freshness_decision",
                "legacy_matrix_binding_status",
                "legacy_matrix_binding_decision",
            )
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "binding_v1_assessment_status": predecessor.get("status"),
            "binding_v1_pairwise_identity_replaced": True,
            "binding_v1_source_projection_replaced": True,
            "native_uncertainty_audit_exactly_rebuilt": uncertainty_exact,
            "adapter_matrix_deterministically_projected_from_native_uncertainty": (
                projected_matrix_identity
            ),
            "shared_native_lineage_verified": passed,
            "adapter_v2_pass_observed": (
                passed and adapter_document.get("status") == "PASS"
            ),
            "session_freshness_pass_observed": (
                passed and freshness_document.get("status") == "PASS"
            ),
            "lineage_binding_only": True,
            "joint_admission_decision_made": False,
            "source_documents_embedded": False,
            "predecessor_diagnostics_embedded": False,
            "completed_price_rows_embedded": False,
            "correlation_matrices_embedded": False,
            "return_series_embedded": False,
            "external_provider_trust_verified": False,
            "external_time_authority_verified": False,
            "profitability_proven": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
        },
        "authority": {
            "current_admission_allowed": False,
            "current_pointer_written": False,
            "descriptive_only": True,
            "formal_registry_activation_allowed": False,
            "live_order_allowed": False,
            "migration_allowed": False,
            "paper_authorized": False,
            "risk_service_invocation_allowed": False,
            "runtime_gate_activation_allowed": False,
            "shadow_consumer_activation_allowed": False,
            "writer_allowed": False,
        },
    }
    return seal_strict_canonical_document(document, "lineage_binding_hash")


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2(
    document: Any,
    adapter_v2_document: Any,
    freshness_evaluation: Any,
    legacy_matrix_binding: Any,
    *,
    adapter_v2_verification_context: Any,
    freshness_verification_context: Any,
    legacy_matrix_binding_verification_context: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2(
        adapter_v2_document,
        freshness_evaluation,
        legacy_matrix_binding,
        adapter_v2_verification_context=adapter_v2_verification_context,
        freshness_verification_context=freshness_verification_context,
        legacy_matrix_binding_verification_context=(
            legacy_matrix_binding_verification_context
        ),
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": BINDING_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["lineage_binding_v2_exact_rebuild_mismatch"],
        "lineage_binding_status": expected["status"] if exact else "UNKNOWN",
        "lineage_binding_exactly_verified": exact,
        "joint_admission_decision_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "runtime_gate_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


__all__ = [
    "BINDING_SCHEMA_VERSION",
    "BINDING_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v2",
]
