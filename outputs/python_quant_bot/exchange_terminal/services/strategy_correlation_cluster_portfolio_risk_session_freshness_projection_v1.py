from __future__ import annotations

from typing import Any

from .strategy_correlation_cluster_portfolio_risk_session_freshness_v1 import (
    EVALUATION_SCHEMA_VERSION,
    verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from .strict_governance_primitives import strict_sha256


PROJECTION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-session-freshness-public-projection-v1"
)
PROJECTION_VERIFICATION_SCHEMA_VERSION = f"{PROJECTION_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260822-session-lag-ledger-projection-lock-1"


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _text_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _int_or_none(value: Any) -> int | None:
    return value if type(value) is int else None


def _bool_or_none(value: Any) -> bool | None:
    return value if type(value) is bool else None


def _authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


def build_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1(
    evaluation_document: Any,
    registration: Any,
    *,
    registration_inputs: Any,
    trusted_clock_attestation: Any,
    expected_trusted_clock_attestation_hash: Any,
) -> dict[str, Any]:
    supplied = evaluation_document is not None
    exact = False
    if type(evaluation_document) is dict:
        try:
            exact = bool(
                evaluation_document.get("schema_version")
                == EVALUATION_SCHEMA_VERSION
                and strict_sha256(evaluation_document.get("evaluation_hash"))
                and verify_strategy_correlation_cluster_portfolio_risk_session_freshness_evaluation_v1(
                    evaluation_document,
                    registration,
                    registration_inputs=registration_inputs,
                    trusted_clock_attestation=trusted_clock_attestation,
                    expected_trusted_clock_attestation_hash=(
                        expected_trusted_clock_attestation_hash
                    ),
                )
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            exact = False

    evaluation = _dict(evaluation_document) if exact else {}
    source = _dict(evaluation.get("source"))
    source_hash_fields = (
        "registration_hash",
        "native_cutoff_manifest_hash",
        "calendar_registration_hash",
        "calendar_session_verification_hash",
        "trusted_clock_attestation_hash",
    )
    source_exact = bool(
        exact and all(strict_sha256(source.get(field)) for field in source_hash_fields)
    )
    status = "OBSERVED" if source_exact else ("UNKNOWN" if supplied else "NOT_SUPPLIED")
    source_state = "VERIFIED" if source_exact else ("UNKNOWN" if supplied else "NOT_SUPPLIED")

    facts = _dict(evaluation.get("facts")) if source_exact else {}
    lag = _dict(evaluation.get("lag")) if source_exact else {}
    cutoff = _dict(evaluation.get("cutoff")) if source_exact else {}
    reference = _dict(evaluation.get("reference")) if source_exact else {}
    lag_evaluated = _bool_or_none(facts.get("freshness_policy_evaluated"))
    within_policy = _bool_or_none(facts.get("session_lag_within_policy"))
    if not supplied:
        gap_state = "NOT_SUPPLIED"
    elif not source_exact:
        gap_state = "UNKNOWN"
    elif lag_evaluated is True and within_policy is True:
        gap_state = "LOCAL_SESSION_LAG_WITHIN_POLICY_EXTERNAL_TIME_AUTHORITY_GAP"
    elif lag_evaluated is True:
        gap_state = "SESSION_LAG_POLICY_GAP_PRESENT"
    else:
        gap_state = "UNVERIFIED_FRESHNESS_EVIDENCE_GAP"

    if source_exact:
        decision = _text_or_none(evaluation.get("decision"))
    else:
        decision = "UNKNOWN" if supplied else "NOT_SUPPLIED"

    document: dict[str, Any] = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "pipeline": [
            {"stage": "SOURCE", "state": source_state},
            {"stage": "GAP", "state": gap_state},
            {"stage": "MATURITY", "state": "UNMOUNTED_CANDIDATE"},
            {"stage": "PERMISSION", "state": "UNAUTHORIZED"},
        ],
        "source": {
            "evaluation_supplied": supplied,
            "evaluation_exactly_verified": exact,
            "complete_source_hash_lineage": source_exact,
            "evaluation_schema_version": (
                EVALUATION_SCHEMA_VERSION if exact else None
            ),
            "evaluation_hash": (
                _text_or_none(evaluation.get("evaluation_hash")) if exact else None
            ),
        },
        "summary": {
            "evaluation_decision": decision,
            "evaluation_status": (
                _text_or_none(evaluation.get("status")) if source_exact else None
            ),
            "cutoff_session_label": (
                _text_or_none(cutoff.get("session_label_date"))
                if source_exact
                else None
            ),
            "reference_time_utc": (
                _text_or_none(reference.get("attested_now_utc"))
                if source_exact
                else None
            ),
            "max_completed_session_lag": (
                _int_or_none(lag.get("max_completed_session_lag"))
                if source_exact
                else None
            ),
            "preregistered_max_completed_session_lag": (
                _int_or_none(lag.get("preregistered_max_completed_session_lag"))
                if source_exact
                else None
            ),
            "calendar_count": (
                _int_or_none(lag.get("calendar_count")) if source_exact else None
            ),
            "clock_quality": (
                _text_or_none(reference.get("clock_quality"))
                if source_exact
                else None
            ),
            "external_clock_source_count": (
                _int_or_none(reference.get("external_clock_source_count"))
                if source_exact
                else None
            ),
            "local_policy_condition_satisfied": (
                _bool_or_none(facts.get("shadow_policy_condition_satisfied"))
                if source_exact
                else None
            ),
            "external_clock_authority_authenticated": (
                _bool_or_none(facts.get("external_clock_authority_authenticated"))
                if source_exact
                else None
            ),
            "freshness_externally_proven": (
                _bool_or_none(facts.get("freshness_externally_proven"))
                if source_exact
                else None
            ),
            "blocker_count": (
                len(_list(evaluation.get("blockers"))) if source_exact else None
            ),
        },
        "facts": {
            "source_documents_embedded": False,
            "clock_sources_embedded": False,
            "calendar_ids_embedded": False,
            "per_calendar_lag_embedded": False,
            "raw_correlations_embedded": False,
            "profitability_proof": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_mounted": False,
            "natural_forward_chain_changed": False,
            "external_time_authority_authenticated": False,
        },
        "authority": _authority(),
    }
    return seal_strict_canonical_document(document, "projection_hash")


def verify_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1(
    document: Any,
    evaluation_document: Any,
    registration: Any,
    *,
    registration_inputs: Any,
    trusted_clock_attestation: Any,
    expected_trusted_clock_attestation_hash: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1(
        evaluation_document,
        registration,
        registration_inputs=registration_inputs,
        trusted_clock_attestation=trusted_clock_attestation,
        expected_trusted_clock_attestation_hash=(
            expected_trusted_clock_attestation_hash
        ),
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": PROJECTION_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["projection_exact_rebuild_mismatch"],
        "projection_status": expected["status"] if exact else "UNKNOWN",
        "projection_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
    }


__all__ = [
    "PROJECTION_SCHEMA_VERSION",
    "PROJECTION_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_session_freshness_projection_v1",
]
