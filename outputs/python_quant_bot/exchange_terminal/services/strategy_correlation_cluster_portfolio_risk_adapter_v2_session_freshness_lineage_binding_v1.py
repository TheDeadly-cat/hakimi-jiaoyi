"""Exact lineage binding for adapter v2 and session-freshness evidence.

The receipt proves shared native replay/cutoff ancestry. It does not combine
component decisions, activate a consumer, or grant trading authority.
"""

from __future__ import annotations

from typing import Any

from .strategy_correlation_cluster_portfolio_risk_adapter_v2 import (
    SCHEMA_VERSION as ADAPTER_V2_SCHEMA_VERSION,
    VERIFICATION_SCHEMA_VERSION as ADAPTER_V2_VERIFICATION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_portfolio_risk_adapter_v2,
)
from .strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1 import (
    BINDING_SCHEMA_VERSION as LEGACY_BINDING_SCHEMA_VERSION,
    BINDING_VERIFICATION_SCHEMA_VERSION as LEGACY_BINDING_VERIFICATION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1,
)
from .strategy_correlation_cluster_portfolio_risk_session_freshness_v1 import (
    EVALUATION_SCHEMA_VERSION as FRESHNESS_EVALUATION_SCHEMA_VERSION,
    REGISTRATION_SCHEMA_VERSION as FRESHNESS_REGISTRATION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


BINDING_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-adapter-v2-"
    "session-freshness-lineage-binding-v1"
)
BINDING_VERIFICATION_SCHEMA_VERSION = f"{BINDING_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260822-portfolio-risk-adapter-freshness-lineage-lock-1"

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


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _exact_dict(value: Any, keys: set[str]) -> dict[str, Any]:
    return value if type(value) is dict and set(value) == keys else {}


def _text_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _authority_locked(value: Any, *, descriptive: bool) -> bool:
    authority = _dict(value)
    if descriptive and authority.get("descriptive_only") is not True:
        return False
    return bool(
        authority
        and all(
            item is False
            for key, item in authority.items()
            if not (descriptive and key == "descriptive_only")
        )
    )


def _check(name: str, ok: bool) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "blocking": True}


def _verify_adapter_v2(document: Any, context: Any) -> bool:
    values = _exact_dict(context, _ADAPTER_V2_CONTEXT_KEYS)
    if type(document) is not dict or not values:
        return False
    try:
        verification = verify_strategy_correlation_cluster_portfolio_risk_adapter_v2(
            document,
            values["adapter_v1_document"],
            values["temporal_stability_gate"],
            adapter_v1_verification_context=values[
                "adapter_v1_verification_context"
            ],
            temporal_stability_verification_context=values[
                "temporal_stability_verification_context"
            ],
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return False
    return bool(
        type(verification) is dict
        and verification.get("schema_version")
        == ADAPTER_V2_VERIFICATION_SCHEMA_VERSION
        and verification.get("status") == "PASS"
        and verification.get("adapter_exactly_verified") is True
        and not _list(verification.get("blockers"))
        and document.get("schema_version") == ADAPTER_V2_SCHEMA_VERSION
        and document.get("status") in {"PASS", "BLOCK"}
        and strict_sha256(document.get("adapter_hash"))
    )


def _verify_freshness(document: Any, context: Any) -> bool:
    values = _exact_dict(context, _FRESHNESS_CONTEXT_KEYS)
    inputs = _exact_dict(values.get("registration_inputs"), _REGISTRATION_INPUT_KEYS)
    registration = _dict(values.get("registration"))
    if type(document) is not dict or not values or not inputs:
        return False
    try:
        exact = verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1(
            document,
            registration,
            registration_inputs=inputs,
            trusted_clock_attestation=values["trusted_clock_attestation"],
            expected_trusted_clock_attestation_hash=values[
                "expected_trusted_clock_attestation_hash"
            ],
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return False
    return bool(
        exact is True
        and document.get("schema_version") == FRESHNESS_EVALUATION_SCHEMA_VERSION
        and document.get("status") in {"PASS", "BLOCK"}
        and strict_sha256(document.get("evaluation_hash"))
        and registration.get("schema_version")
        == FRESHNESS_REGISTRATION_SCHEMA_VERSION
        and registration.get("status") == "REGISTERED"
        and strict_sha256(registration.get("registration_hash"))
    )


def _verify_legacy_binding(document: Any, context: Any) -> bool:
    values = _exact_dict(context, _LEGACY_CONTEXT_KEYS)
    if type(document) is not dict or not values:
        return False
    try:
        verification = verify_strategy_correlation_cluster_portfolio_risk_legacy_matrix_derivation_binding_v1(
            document,
            values["legacy_correlation_matrix"],
            values["completed_price_input"],
            values["matrix_replay"],
            values["derivation_receipt"],
            values["composition_document"],
            values["composition_context"],
            values["dataset_attestation_verification"],
            values["dataset_attestation_registration"],
            values["provider_dataset_public_key_base64"],
            values["dataset_attestation_receipt"],
            expected_registration_hash=values["expected_registration_hash"],
            expected_attestation_hash=values["expected_attestation_hash"],
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return False
    return bool(
        type(verification) is dict
        and verification.get("schema_version")
        == LEGACY_BINDING_VERIFICATION_SCHEMA_VERSION
        and verification.get("status") == "PASS"
        and verification.get("binding_exactly_verified") is True
        and not _list(verification.get("blockers"))
        and document.get("schema_version") == LEGACY_BINDING_SCHEMA_VERSION
        and document.get("status") == "PASS"
        and strict_sha256(document.get("binding_hash"))
    )


def _legacy_projection(value: Any) -> dict[str, Any] | None:
    matrix = _dict(value)
    pairs = _dict(matrix.get("pairs"))
    if not pairs:
        return None
    projected: dict[str, int | float] = {}
    for key in sorted(pairs):
        item = _dict(pairs[key])
        correlation = item.get("correlation")
        if (
            type(key) is not str
            or not key
            or type(correlation) not in (int, float)
        ):
            return None
        projected[key] = correlation
    return {"pairs": projected}


def build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1(
    adapter_v2_document: Any,
    freshness_evaluation: Any,
    legacy_matrix_binding: Any,
    *,
    adapter_v2_verification_context: Any,
    freshness_verification_context: Any,
    legacy_matrix_binding_verification_context: Any,
) -> dict[str, Any]:
    adapter_context = _exact_dict(
        adapter_v2_verification_context, _ADAPTER_V2_CONTEXT_KEYS
    )
    adapter_v1_context = _exact_dict(
        adapter_context.get("adapter_v1_verification_context"),
        _ADAPTER_V1_CONTEXT_KEYS,
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

    adapter_exact = _verify_adapter_v2(
        adapter_v2_document, adapter_v2_verification_context
    )
    freshness_exact = _verify_freshness(
        freshness_evaluation, freshness_verification_context
    )
    legacy_exact = _verify_legacy_binding(
        legacy_matrix_binding, legacy_matrix_binding_verification_context
    )

    matrix_replay = _dict(native_context.get("matrix_replay"))
    native_preregistration = _dict(matrix_replay.get("preregistration"))
    native_pairwise_matrix = _dict(matrix_replay.get("correlation_matrix"))
    adapter_native_preregistration = bool(
        adapter_v1_context
        and native_preregistration
        and strict_json_contract_equal(
            adapter_v1_context.get("preregistration"),
            native_preregistration,
        )
    )
    adapter_native_pairwise_matrix = bool(
        adapter_v1_context
        and native_pairwise_matrix
        and strict_json_contract_equal(
            adapter_v1_context.get("cluster_correlation_matrix"),
            native_pairwise_matrix,
        )
    )

    projected_legacy = _legacy_projection(
        legacy_context.get("legacy_correlation_matrix")
    )
    adapter_legacy_projection = bool(
        adapter_v1_context
        and projected_legacy is not None
        and strict_json_contract_equal(
            adapter_v1_context.get("legacy_correlations"),
            projected_legacy,
        )
    )

    native_chain_exact = bool(
        native_context
        and legacy_context
        and all(
            strict_json_contract_equal(native_context.get(key), legacy_context.get(key))
            for key in (
                "completed_price_input",
                "matrix_replay",
                "derivation_receipt",
                "composition_document",
                "composition_context",
            )
        )
    )

    native_manifest = _dict(registration_inputs.get("native_cutoff_manifest"))
    registration = _dict(freshness_context.get("registration"))
    freshness_source = _dict(_dict(freshness_evaluation).get("source"))
    registration_source = _dict(registration.get("source"))
    manifest_hash = native_manifest.get("manifest_hash")
    registration_hash = registration.get("registration_hash")
    native_manifest_continuity = bool(
        strict_sha256(manifest_hash)
        and registration_inputs.get("expected_native_cutoff_manifest_hash")
        == manifest_hash
        and registration_source.get("native_cutoff_manifest_hash") == manifest_hash
        and freshness_source.get("native_cutoff_manifest_hash") == manifest_hash
        and strict_sha256(registration_hash)
        and freshness_source.get("registration_hash") == registration_hash
    )

    completed_input = _dict(native_context.get("completed_price_input"))
    expected_cutoff = native_context.get("expected_observation_cutoff_utc")
    manifest_cutoff = _dict(native_manifest.get("cutoff"))
    legacy_portfolio_matrix = _dict(_dict(legacy_matrix_binding).get("portfolio_matrix"))
    cutoff_continuity = bool(
        type(completed_input.get("cutoff_date")) is str
        and expected_cutoff == f"{completed_input['cutoff_date']}T00:00:00Z"
        and manifest_cutoff.get("observation_cutoff_utc") == expected_cutoff
        and manifest_cutoff.get("session_label_date")
        == completed_input.get("cutoff_date")
        and legacy_portfolio_matrix.get("cutoff_date")
        == completed_input.get("cutoff_date")
    )

    adapter_source = _dict(_dict(adapter_v2_document).get("source"))
    legacy_source = _dict(_dict(legacy_matrix_binding).get("source"))
    source_hash_projection = bool(
        strict_sha256(native_preregistration.get("preregistration_hash"))
        and adapter_source.get("preregistration_hash")
        == native_preregistration.get("preregistration_hash")
        and strict_sha256(native_pairwise_matrix.get("matrix_hash"))
        and adapter_source.get("correlation_matrix_hash")
        == native_pairwise_matrix.get("matrix_hash")
        and strict_sha256(_dict(legacy_context.get("legacy_correlation_matrix")).get("matrix_hash"))
        and legacy_source.get("legacy_matrix_hash")
        == _dict(legacy_context.get("legacy_correlation_matrix")).get("matrix_hash")
        and legacy_source.get("preregistration_hash")
        == native_preregistration.get("preregistration_hash")
        and legacy_source.get("completed_price_input_hash")
        == completed_input.get("input_hash")
        and legacy_source.get("matrix_replay_hash") == matrix_replay.get("replay_hash")
    )

    adapter_facts = _dict(_dict(adapter_v2_document).get("facts"))
    freshness_facts = _dict(_dict(freshness_evaluation).get("facts"))
    legacy_facts = _dict(_dict(legacy_matrix_binding).get("facts"))
    external_trust_locked = bool(
        _authority_locked(_dict(adapter_v2_document).get("authority"), descriptive=True)
        and _authority_locked(
            _dict(legacy_matrix_binding).get("authority"), descriptive=True
        )
        and _authority_locked(
            _dict(freshness_evaluation).get("authority"), descriptive=False
        )
        and adapter_facts.get("profitability_proven") is False
        and freshness_facts.get("external_clock_authority_authenticated") is False
        and freshness_facts.get("freshness_externally_proven") is False
        and legacy_facts.get("external_provider_dataset_key_control_verified")
        is False
        and legacy_facts.get("external_provider_data_issuance_verified") is False
        and legacy_facts.get("profitability_verified") is False
    )

    checks = [
        _check("adapter_v2_exact_verification", adapter_exact),
        _check("session_freshness_exact_verification", freshness_exact),
        _check("legacy_matrix_binding_exact_verification", legacy_exact),
        _check("adapter_native_preregistration_identity", adapter_native_preregistration),
        _check("adapter_native_pairwise_matrix_identity", adapter_native_pairwise_matrix),
        _check("adapter_legacy_matrix_projection_identity", adapter_legacy_projection),
        _check("freshness_legacy_native_document_chain", native_chain_exact),
        _check("native_manifest_registration_evaluation_hash_chain", native_manifest_continuity),
        _check("native_cutoff_date_continuity", cutoff_continuity),
        _check("public_source_hash_projection", source_hash_projection),
        _check("external_trust_and_authority_not_promoted", external_trust_locked),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    passed = not blockers

    adapter_document = _dict(adapter_v2_document)
    freshness_document = _dict(freshness_evaluation)
    legacy_document = _dict(legacy_matrix_binding)
    source_hashes_available = bool(
        passed
        and strict_sha256(manifest_hash)
        and strict_sha256(registration_hash)
    )
    document: dict[str, Any] = {
        "schema_version": BINDING_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PASS" if passed else "BLOCK",
        "decision": (
            "EXACT_NATIVE_LINEAGE_BOUND_COMPONENT_DECISIONS_NOT_PROMOTED_"
            "EXTERNAL_TRUST_UNPROVEN"
            if passed
            else "BLOCKED_ADAPTER_FRESHNESS_LINEAGE_BINDING"
        ),
        "source": {
            "adapter_v2_hash": (
                _text_or_none(adapter_document.get("adapter_hash"))
                if source_hashes_available
                else None
            ),
            "freshness_evaluation_hash": (
                _text_or_none(freshness_document.get("evaluation_hash"))
                if source_hashes_available
                else None
            ),
            "legacy_matrix_binding_hash": (
                _text_or_none(legacy_document.get("binding_hash"))
                if source_hashes_available
                else None
            ),
            "native_cutoff_manifest_hash": (
                manifest_hash if source_hashes_available else None
            ),
            "freshness_registration_hash": (
                registration_hash if source_hashes_available else None
            ),
            "completed_price_input_hash": (
                _text_or_none(completed_input.get("input_hash"))
                if source_hashes_available
                else None
            ),
            "matrix_replay_hash": (
                _text_or_none(matrix_replay.get("replay_hash"))
                if source_hashes_available
                else None
            ),
            "preregistration_hash": (
                _text_or_none(native_preregistration.get("preregistration_hash"))
                if source_hashes_available
                else None
            ),
            "correlation_matrix_hash": (
                _text_or_none(native_pairwise_matrix.get("matrix_hash"))
                if source_hashes_available
                else None
            ),
            "legacy_matrix_hash": (
                _text_or_none(
                    _dict(legacy_context.get("legacy_correlation_matrix")).get(
                        "matrix_hash"
                    )
                )
                if source_hashes_available
                else None
            ),
            "observation_cutoff_utc": (
                expected_cutoff
                if source_hashes_available and type(expected_cutoff) is str
                else None
            ),
        },
        "component_states": {
            "adapter_v2_status": (
                _text_or_none(adapter_document.get("status"))
                if adapter_exact
                else "UNKNOWN"
            ),
            "adapter_v2_decision": (
                _text_or_none(adapter_document.get("decision"))
                if adapter_exact
                else "UNKNOWN"
            ),
            "session_freshness_status": (
                _text_or_none(freshness_document.get("status"))
                if freshness_exact
                else "UNKNOWN"
            ),
            "session_freshness_decision": (
                _text_or_none(freshness_document.get("decision"))
                if freshness_exact
                else "UNKNOWN"
            ),
            "legacy_matrix_binding_status": (
                _text_or_none(legacy_document.get("status"))
                if legacy_exact
                else "UNKNOWN"
            ),
            "legacy_matrix_binding_decision": (
                _text_or_none(legacy_document.get("decision"))
                if legacy_exact
                else "UNKNOWN"
            ),
        },
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "adapter_v2_exactly_verified": adapter_exact,
            "session_freshness_exactly_verified": freshness_exact,
            "legacy_matrix_binding_exactly_verified": legacy_exact,
            "shared_native_lineage_verified": passed,
            "adapter_v2_pass_observed": (
                adapter_exact and adapter_document.get("status") == "PASS"
            ),
            "session_freshness_pass_observed": (
                freshness_exact and freshness_document.get("status") == "PASS"
            ),
            "lineage_binding_only": True,
            "joint_admission_decision_made": False,
            "source_documents_embedded": False,
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


def verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1(
    document: Any,
    adapter_v2_document: Any,
    freshness_evaluation: Any,
    legacy_matrix_binding: Any,
    *,
    adapter_v2_verification_context: Any,
    freshness_verification_context: Any,
    legacy_matrix_binding_verification_context: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1(
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
        "blockers": [] if exact else ["lineage_binding_exact_rebuild_mismatch"],
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
    "build_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_adapter_v2_session_freshness_lineage_binding_v1",
]
