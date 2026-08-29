from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import strategy_correlation_cluster_effective_bet_budget_v5 as budget_v5
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)


STATIC_FINGERPRINT = (
    "20260824-portfolio-snapshot-continuity-freshness-effective-budget-v6-"
    "synthetic-lock-1"
)
POLICY_SCHEMA_VERSION = (
    "strategy-correlation-portfolio-snapshot-admission-policy-v1"
)
STATE_SCHEMA_VERSION = "strategy-correlation-portfolio-snapshot-admission-state-v1"
TRANSITION_SCHEMA_VERSION = (
    "strategy-correlation-portfolio-snapshot-admission-transition-v1"
)
BUDGET_SCHEMA_VERSION = "strategy-correlation-cluster-effective-bet-budget-v6"

_MAX_TIME_MS = 9_999_999_999_999_999
_MAX_AGE_MS = 86_400_000
_MAX_FUTURE_SKEW_MS = 300_000
_LIMITATIONS = [
    "SNAPSHOT_PROVIDER_IDENTITY_UNVERIFIED",
    "SNAPSHOT_PROVIDER_IMPLEMENTATION_UNVERIFIED",
    "SNAPSHOT_SOURCE_TRUTH_UNVERIFIED",
    "TRUSTED_EVALUATION_CLOCK_UNVERIFIED",
    "ATOMIC_CURRENT_HEAD_PERSISTENCE_UNVERIFIED",
    "CURRENT_ACTIVATION_UNAUTHORIZED",
]


def _locked_authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "snapshot_source_trust_allowed": False,
        "runtime_gate_activation_allowed": False,
        "migration_allowed": False,
        "writer_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return deepcopy(value)


def _require_int(
    value: Any,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = _MAX_TIME_MS,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < minimum or value > maximum:
        raise ValueError(f"{field} is outside the allowed range")
    return value


def _require_sha256(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _document_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _document_sha256(value: Any) -> str | None:
    try:
        return _require_sha256(value, "document hash")
    except ValueError:
        return None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check(check_id: str, passed: bool) -> dict[str, str]:
    return {"check_id": check_id, "status": "PASS" if passed else "BLOCK"}


def _blockers(checks: list[dict[str, str]]) -> list[str]:
    return [item["check_id"] for item in checks if item["status"] != "PASS"]


def build_portfolio_snapshot_admission_policy_v1(
    provider_preregistration_document: Any,
    *,
    provider_preregistration_kwargs: Any,
    maximum_snapshot_age_ms: Any,
    maximum_future_skew_ms: Any,
) -> dict[str, Any]:
    provider_kwargs = _require_mapping(
        provider_preregistration_kwargs,
        "provider_preregistration_kwargs",
    )
    if not budget_v5.verify_portfolio_snapshot_provider_preregistration_v1(
        provider_preregistration_document,
        **provider_kwargs,
    ):
        raise ValueError("provider preregistration is not exact")

    maximum_age = _require_int(
        maximum_snapshot_age_ms,
        "maximum_snapshot_age_ms",
        minimum=1,
        maximum=_MAX_AGE_MS,
    )
    maximum_future_skew = _require_int(
        maximum_future_skew_ms,
        "maximum_future_skew_ms",
        maximum=_MAX_FUTURE_SKEW_MS,
    )
    if maximum_future_skew > maximum_age:
        raise ValueError("maximum_future_skew_ms cannot exceed maximum_snapshot_age_ms")

    provider = _mapping(provider_preregistration_document)
    identity = _mapping(provider.get("identity"))
    provider_hash = _require_sha256(
        provider.get("provider_preregistration_hash"),
        "provider_preregistration_hash",
    )
    account_scope_hash = _require_sha256(
        identity.get("account_scope_hash"),
        "account_scope_hash",
    )

    document = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED",
        "decision": (
            "LOCAL_SEQUENCE_AND_FRESHNESS_POLICY_PREREGISTERED_"
            "CLOCK_HEAD_AND_SOURCE_TRUTH_UNVERIFIED"
        ),
        "source": {
            "provider_preregistration_hash": provider_hash,
            "account_scope_hash": account_scope_hash,
        },
        "continuity_policy": {
            "sequence_rule": "EXACT_PREVIOUS_PLUS_ONE",
            "exact_sequence_increment": 1,
            "observed_time_rule": "STRICTLY_INCREASING",
            "maximum_snapshot_age_ms": maximum_age,
            "maximum_future_skew_ms": maximum_future_skew,
            "current_head_rule": "EXACT_EXTERNAL_EXPECTED_STATE_HASH",
        },
        "facts": {
            "provider_preregistration_exact": True,
            "local_policy_shape_exact": True,
            "trusted_evaluation_clock_verified": False,
            "atomic_current_head_persistence_verified": False,
            "snapshot_source_truth_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "policy_hash")


def verify_portfolio_snapshot_admission_policy_v1(
    document: Any,
    provider_preregistration_document: Any,
    *,
    expected_policy_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(expected_policy_hash, "expected_policy_hash")
        rebuilt = build_portfolio_snapshot_admission_policy_v1(
            provider_preregistration_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("policy_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def build_portfolio_snapshot_admission_state_v1(
    policy_document: Any,
    provider_preregistration_document: Any,
    *,
    expected_policy_hash: Any,
    policy_build_kwargs: Any,
    state_revision: Any,
    last_snapshot_claim_hash: Any,
    last_snapshot_sequence: Any,
    last_observed_at_unix_ms: Any,
) -> dict[str, Any]:
    policy_kwargs = _require_mapping(policy_build_kwargs, "policy_build_kwargs")
    policy_hash = _require_sha256(expected_policy_hash, "expected_policy_hash")
    if not verify_portfolio_snapshot_admission_policy_v1(
        policy_document,
        provider_preregistration_document,
        expected_policy_hash=policy_hash,
        **policy_kwargs,
    ):
        raise ValueError("admission policy is not exact")

    revision = _require_int(state_revision, "state_revision")
    claim_hash = _require_sha256(
        last_snapshot_claim_hash,
        "last_snapshot_claim_hash",
    )
    sequence = _require_int(last_snapshot_sequence, "last_snapshot_sequence")
    observed_at = _require_int(
        last_observed_at_unix_ms,
        "last_observed_at_unix_ms",
    )
    policy = _mapping(policy_document)
    policy_source = _mapping(policy.get("source"))

    document = {
        "schema_version": STATE_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "CANDIDATE",
        "decision": (
            "LOCAL_SNAPSHOT_HEAD_STATE_CANDIDATE_"
            "ATOMIC_PERSISTENCE_AND_SOURCE_TRUTH_UNVERIFIED"
        ),
        "source": {
            "policy_hash": policy_hash,
            "provider_preregistration_hash": _require_sha256(
                policy_source.get("provider_preregistration_hash"),
                "provider_preregistration_hash",
            ),
            "account_scope_hash": _require_sha256(
                policy_source.get("account_scope_hash"),
                "account_scope_hash",
            ),
        },
        "state": {
            "state_revision": revision,
            "last_snapshot_claim_hash": claim_hash,
            "last_snapshot_sequence": sequence,
            "last_observed_at_unix_ms": observed_at,
        },
        "facts": {
            "local_state_shape_exact": True,
            "policy_exact": True,
            "external_current_head_verified": False,
            "atomic_current_head_persistence_verified": False,
            "snapshot_source_truth_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "state_hash")


def verify_portfolio_snapshot_admission_state_v1(
    document: Any,
    policy_document: Any,
    provider_preregistration_document: Any,
    *,
    expected_state_hash: Any,
    **build_kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(expected_state_hash, "expected_state_hash")
        rebuilt = build_portfolio_snapshot_admission_state_v1(
            policy_document,
            provider_preregistration_document,
            **build_kwargs,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        rebuilt.get("state_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_portfolio_snapshot_admission_transition_v1(
    previous_state_document: Any,
    policy_document: Any,
    snapshot_evidence_document: Any,
    signed_snapshot_document: Any,
    snapshot_claim_document: Any,
    provider_preregistration_document: Any,
    *,
    expected_previous_state_hash: Any,
    previous_state_build_kwargs: Any,
    expected_snapshot_evidence_hash: Any,
    snapshot_evaluation_kwargs: Any,
    evaluated_at_unix_ms: Any,
) -> dict[str, Any]:
    previous_state_hash = _require_sha256(
        expected_previous_state_hash,
        "expected_previous_state_hash",
    )
    snapshot_evidence_hash = _require_sha256(
        expected_snapshot_evidence_hash,
        "expected_snapshot_evidence_hash",
    )
    evaluation_time = _require_int(
        evaluated_at_unix_ms,
        "evaluated_at_unix_ms",
    )
    state_kwargs = _require_mapping(
        previous_state_build_kwargs,
        "previous_state_build_kwargs",
    )
    snapshot_kwargs = _require_mapping(
        snapshot_evaluation_kwargs,
        "snapshot_evaluation_kwargs",
    )

    previous_state_exact = verify_portfolio_snapshot_admission_state_v1(
        previous_state_document,
        policy_document,
        provider_preregistration_document,
        expected_state_hash=previous_state_hash,
        **state_kwargs,
    )
    try:
        signature_evidence_exact = (
            budget_v5.verify_signed_portfolio_snapshot_evidence_v1(
                snapshot_evidence_document,
                signed_snapshot_document,
                snapshot_claim_document,
                provider_preregistration_document,
                expected_snapshot_evidence_hash=snapshot_evidence_hash,
                **snapshot_kwargs,
            )
        )
    except Exception:
        signature_evidence_exact = False

    previous_state = _mapping(previous_state_document)
    previous_payload = _mapping(previous_state.get("state"))
    previous_source = _mapping(previous_state.get("source"))
    policy = _mapping(policy_document)
    policy_source = _mapping(policy.get("source"))
    continuity_policy = _mapping(policy.get("continuity_policy"))
    evidence = _mapping(snapshot_evidence_document)
    evidence_source = _mapping(evidence.get("source"))
    snapshot_summary = _mapping(evidence.get("snapshot_summary"))
    evidence_facts = _mapping(evidence.get("facts"))

    previous_revision = _document_int(previous_payload.get("state_revision"))
    previous_sequence = _document_int(previous_payload.get("last_snapshot_sequence"))
    previous_observed_at = _document_int(
        previous_payload.get("last_observed_at_unix_ms")
    )
    previous_claim_hash = _document_sha256(
        previous_payload.get("last_snapshot_claim_hash")
    )
    candidate_sequence = _document_int(snapshot_summary.get("snapshot_sequence"))
    candidate_observed_at = _document_int(snapshot_summary.get("observed_at_unix_ms"))
    candidate_claim_hash = _document_sha256(
        evidence_source.get("snapshot_claim_hash")
    )
    maximum_age = _document_int(
        continuity_policy.get("maximum_snapshot_age_ms")
    )
    maximum_future_skew = _document_int(
        continuity_policy.get("maximum_future_skew_ms")
    )

    evidence_pass = bool(
        signature_evidence_exact
        and evidence.get("status") == "PASS"
        and evidence_facts.get("cryptographic_signature_verified") is True
        and evidence_facts.get("preregistered_provider_key_signature_verified") is True
    )
    provider_binding_exact = bool(
        previous_state_exact
        and signature_evidence_exact
        and evidence_source.get("provider_preregistration_hash")
        == previous_source.get("provider_preregistration_hash")
        == policy_source.get("provider_preregistration_hash")
    )
    sequence_exact = bool(
        previous_sequence is not None
        and candidate_sequence is not None
        and candidate_sequence == previous_sequence + 1
    )
    observed_time_monotonic = bool(
        previous_observed_at is not None
        and candidate_observed_at is not None
        and candidate_observed_at > previous_observed_at
    )
    claim_advances = bool(
        previous_claim_hash is not None
        and candidate_claim_hash is not None
        and candidate_claim_hash != previous_claim_hash
    )
    clock_delta_ms = (
        evaluation_time - candidate_observed_at
        if candidate_observed_at is not None
        else None
    )
    not_too_old = bool(
        clock_delta_ms is not None
        and maximum_age is not None
        and clock_delta_ms <= maximum_age
    )
    not_too_far_future = bool(
        clock_delta_ms is not None
        and maximum_future_skew is not None
        and -clock_delta_ms <= maximum_future_skew
    )

    checks = [
        _check("PREVIOUS_STATE_EXACT", previous_state_exact),
        _check("SNAPSHOT_SIGNATURE_EVIDENCE_EXACT", signature_evidence_exact),
        _check("SNAPSHOT_SIGNATURE_PASS", evidence_pass),
        _check("PROVIDER_BINDING_EXACT", provider_binding_exact),
        _check("SNAPSHOT_CLAIM_ADVANCES", claim_advances),
        _check("SNAPSHOT_SEQUENCE_INCREMENT_EXACT", sequence_exact),
        _check("SNAPSHOT_OBSERVED_TIME_MONOTONIC", observed_time_monotonic),
        _check("SNAPSHOT_NOT_TOO_OLD", not_too_old),
        _check("SNAPSHOT_NOT_TOO_FAR_FUTURE", not_too_far_future),
    ]
    local_transition_pass = not _blockers(checks)

    next_state_candidate: dict[str, Any] | None = None
    if (
        local_transition_pass
        and previous_revision is not None
        and candidate_claim_hash is not None
        and candidate_sequence is not None
        and candidate_observed_at is not None
    ):
        policy_build_kwargs = _mapping(state_kwargs.get("policy_build_kwargs"))
        next_state_candidate = build_portfolio_snapshot_admission_state_v1(
            policy_document,
            provider_preregistration_document,
            expected_policy_hash=_require_sha256(
                previous_source.get("policy_hash"),
                "policy_hash",
            ),
            policy_build_kwargs=policy_build_kwargs,
            state_revision=previous_revision + 1,
            last_snapshot_claim_hash=candidate_claim_hash,
            last_snapshot_sequence=candidate_sequence,
            last_observed_at_unix_ms=candidate_observed_at,
        )

    next_state_hash = (
        next_state_candidate.get("state_hash")
        if isinstance(next_state_candidate, dict)
        else None
    )
    status = "PASS" if local_transition_pass else "BLOCKED"
    document = {
        "schema_version": TRANSITION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": (
            "PASS_LOCAL_SNAPSHOT_HEAD_TRANSITION_"
            "CLOCK_ATOMIC_HEAD_AND_SOURCE_TRUTH_UNVERIFIED"
            if local_transition_pass
            else "BLOCK_SNAPSHOT_HEAD_TRANSITION_CONTRACT"
        ),
        "source": {
            "policy_hash": _document_sha256(policy.get("policy_hash")),
            "provider_preregistration_hash": _document_sha256(
                evidence_source.get("provider_preregistration_hash")
            ),
            "previous_state_hash": previous_state_hash,
            "snapshot_evidence_hash": snapshot_evidence_hash,
            "signed_snapshot_hash": _document_sha256(
                evidence_source.get("signed_snapshot_hash")
            ),
            "snapshot_claim_hash": candidate_claim_hash,
        },
        "transition_summary": {
            "evaluated_at_unix_ms": evaluation_time,
            "clock_delta_ms": clock_delta_ms,
            "previous_state_revision": previous_revision,
            "previous_snapshot_sequence": previous_sequence,
            "candidate_snapshot_sequence": candidate_sequence,
            "previous_observed_at_unix_ms": previous_observed_at,
            "candidate_observed_at_unix_ms": candidate_observed_at,
        },
        "checks": checks,
        "facts": {
            "previous_state_exact": previous_state_exact,
            "snapshot_signature_evidence_exact": signature_evidence_exact,
            "snapshot_sequence_transition_arithmetic_verified": bool(
                sequence_exact and observed_time_monotonic and claim_advances
            ),
            "snapshot_freshness_window_arithmetic_verified": bool(
                not_too_old and not_too_far_future
            ),
            "snapshot_sequence_continuity_verified": False,
            "snapshot_freshness_verified": False,
            "trusted_evaluation_clock_verified": False,
            "atomic_current_head_persistence_verified": False,
            "snapshot_source_truth_verified": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "next_state_hash": next_state_hash,
        "next_state_candidate": deepcopy(next_state_candidate),
        "blockers": _blockers(checks),
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "transition_hash")


def verify_portfolio_snapshot_admission_transition_v1(
    document: Any,
    *args: Any,
    expected_transition_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_transition_hash,
            "expected_transition_hash",
        )
        rebuilt = evaluate_portfolio_snapshot_admission_transition_v1(
            *args,
            **kwargs,
        )
    except Exception:
        return False
    return (
        rebuilt.get("transition_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )


def evaluate_strategy_correlation_cluster_effective_bet_budget_v6(
    transition_document: Any,
    previous_state_document: Any,
    policy_document: Any,
    snapshot_evidence_document: Any,
    signed_snapshot_document: Any,
    snapshot_claim_document: Any,
    provider_preregistration_document: Any,
    correlation_preregistration: Any,
    correlation_matrix: Any,
    complete_link_audit: Any,
    *,
    expected_transition_hash: Any,
    transition_evaluation_kwargs: Any,
    expected_current_state_hash: Any,
    expected_snapshot_evidence_hash: Any,
    snapshot_evaluation_kwargs: Any,
    evaluated_at_unix_ms: Any,
    strata_registration: Any = None,
    strata_gate: Any = None,
    complete_link_gate: Any = None,
    proposed_symbol: Any,
    proposed_notional: Any,
    proposed_direction: Any = "LONG",
    max_cluster_gross_pct: Any = 45.0,
    risk_increasing: Any = True,
    positions_after: Any = None,
    risk_reduction_transition: Any = None,
) -> dict[str, Any]:
    transition_hash = _require_sha256(
        expected_transition_hash,
        "expected_transition_hash",
    )
    current_state_hash = _require_sha256(
        expected_current_state_hash,
        "expected_current_state_hash",
    )
    snapshot_evidence_hash = _require_sha256(
        expected_snapshot_evidence_hash,
        "expected_snapshot_evidence_hash",
    )
    evaluation_time = _require_int(
        evaluated_at_unix_ms,
        "evaluated_at_unix_ms",
    )
    transition_kwargs = _require_mapping(
        transition_evaluation_kwargs,
        "transition_evaluation_kwargs",
    )
    snapshot_kwargs = _require_mapping(
        snapshot_evaluation_kwargs,
        "snapshot_evaluation_kwargs",
    )

    transition_exact = verify_portfolio_snapshot_admission_transition_v1(
        transition_document,
        previous_state_document,
        policy_document,
        snapshot_evidence_document,
        signed_snapshot_document,
        snapshot_claim_document,
        provider_preregistration_document,
        expected_transition_hash=transition_hash,
        **transition_kwargs,
    )
    try:
        budget_v5_result = (
            budget_v5.evaluate_strategy_correlation_cluster_effective_bet_budget_v5(
                snapshot_evidence_document,
                signed_snapshot_document,
                snapshot_claim_document,
                provider_preregistration_document,
                correlation_preregistration,
                correlation_matrix,
                complete_link_audit,
                expected_snapshot_evidence_hash=snapshot_evidence_hash,
                snapshot_evaluation_kwargs=snapshot_kwargs,
                strata_registration=strata_registration,
                strata_gate=strata_gate,
                complete_link_gate=complete_link_gate,
                proposed_symbol=proposed_symbol,
                proposed_notional=proposed_notional,
                proposed_direction=proposed_direction,
                max_cluster_gross_pct=max_cluster_gross_pct,
                risk_increasing=risk_increasing,
                positions_after=positions_after,
                risk_reduction_transition=risk_reduction_transition,
            )
        )
    except Exception:
        budget_v5_result = {}

    transition = _mapping(transition_document)
    transition_source = _mapping(transition.get("source"))
    transition_summary = _mapping(transition.get("transition_summary"))
    transition_facts = _mapping(transition.get("facts"))
    next_state = _mapping(transition.get("next_state_candidate"))
    next_state_payload = _mapping(next_state.get("state"))
    policy = _mapping(policy_document)
    continuity_policy = _mapping(policy.get("continuity_policy"))
    v5_result = _mapping(budget_v5_result)
    v5_source = _mapping(v5_result.get("source"))
    v5_summary = _mapping(v5_result.get("snapshot_summary"))

    transition_pass = bool(transition_exact and transition.get("status") == "PASS")
    current_head_matches = bool(
        transition_pass
        and transition.get("next_state_hash") == current_state_hash
        and next_state.get("state_hash") == current_state_hash
    )
    v5_pass = bool(
        v5_result.get("status") == "PASS"
        and v5_result.get("blockers") == []
    )
    v5_authority = _mapping(v5_result.get("authority"))
    v5_admission_locked = bool(
        v5_result.get("admission_status") == "BLOCKED"
        and v5_authority.get("current_admission_allowed") is False
        and v5_authority.get("paper_authorized") is False
        and v5_authority.get("live_order_allowed") is False
    )
    source_binding_exact = bool(
        transition_pass
        and v5_source.get("snapshot_evidence_hash")
        == transition_source.get("snapshot_evidence_hash")
        == snapshot_evidence_hash
        and v5_source.get("signed_snapshot_hash")
        == transition_source.get("signed_snapshot_hash")
        and v5_source.get("snapshot_claim_hash")
        == transition_source.get("snapshot_claim_hash")
        and v5_source.get("provider_preregistration_hash")
        == transition_source.get("provider_preregistration_hash")
    )
    state_binding_exact = bool(
        current_head_matches
        and next_state_payload.get("last_snapshot_claim_hash")
        == v5_source.get("snapshot_claim_hash")
        and next_state_payload.get("last_snapshot_sequence")
        == v5_summary.get("snapshot_sequence")
        and next_state_payload.get("last_observed_at_unix_ms")
        == v5_summary.get("observed_at_unix_ms")
    )

    observed_at = _document_int(v5_summary.get("observed_at_unix_ms"))
    maximum_age = _document_int(
        continuity_policy.get("maximum_snapshot_age_ms")
    )
    maximum_future_skew = _document_int(
        continuity_policy.get("maximum_future_skew_ms")
    )
    transition_evaluated_at = _document_int(
        transition_summary.get("evaluated_at_unix_ms")
    )
    clock_delta_ms = (
        evaluation_time - observed_at if observed_at is not None else None
    )
    not_too_old = bool(
        clock_delta_ms is not None
        and maximum_age is not None
        and clock_delta_ms <= maximum_age
    )
    not_too_far_future = bool(
        clock_delta_ms is not None
        and maximum_future_skew is not None
        and -clock_delta_ms <= maximum_future_skew
    )
    evaluation_time_monotonic = bool(
        transition_evaluated_at is not None
        and evaluation_time >= transition_evaluated_at
    )

    checks = [
        _check("SNAPSHOT_TRANSITION_EXACT", transition_exact),
        _check("SNAPSHOT_TRANSITION_PASS", transition_pass),
        _check("EXPECTED_CURRENT_HEAD_MATCHES", current_head_matches),
        _check("V5_EFFECTIVE_BUDGET_PASS", v5_pass),
        _check("V5_ADMISSION_AUTHORITY_REMAINS_BLOCKED", v5_admission_locked),
        _check("TRANSITION_SNAPSHOT_SOURCE_BINDING_EXACT", source_binding_exact),
        _check("CURRENT_STATE_SNAPSHOT_BINDING_EXACT", state_binding_exact),
        _check("CURRENT_SNAPSHOT_NOT_TOO_OLD", not_too_old),
        _check("CURRENT_SNAPSHOT_NOT_TOO_FAR_FUTURE", not_too_far_future),
        _check("EVALUATION_TIME_NOT_BEFORE_TRANSITION", evaluation_time_monotonic),
    ]
    local_budget_pass = not _blockers(checks)
    status = "PASS" if local_budget_pass else "BLOCKED"
    document = {
        "schema_version": BUDGET_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "admission_status": "BLOCKED",
        "decision": (
            "PASS_CURRENT_SNAPSHOT_HEAD_BOUND_EFFECTIVE_BUDGET_"
            "CLOCK_ATOMIC_HEAD_AND_SOURCE_TRUTH_UNVERIFIED"
            if local_budget_pass
            else "BLOCK_CURRENT_SNAPSHOT_HEAD_OR_EFFECTIVE_BUDGET_CONTRACT"
        ),
        "source": {
            "policy_hash": _document_sha256(policy.get("policy_hash")),
            "transition_hash": transition_hash,
            "current_state_hash": current_state_hash,
            "snapshot_evidence_hash": snapshot_evidence_hash,
            "signed_snapshot_hash": _document_sha256(
                v5_source.get("signed_snapshot_hash")
            ),
            "snapshot_claim_hash": _document_sha256(
                v5_source.get("snapshot_claim_hash")
            ),
            "provider_preregistration_hash": _document_sha256(
                v5_source.get("provider_preregistration_hash")
            ),
            "v5_budget_hash": _document_sha256(v5_result.get("budget_v5_hash")),
        },
        "snapshot_summary": {
            "snapshot_id_hash": _document_sha256(
                v5_summary.get("snapshot_id_hash")
            ),
            "snapshot_sequence": _document_int(v5_summary.get("snapshot_sequence")),
            "observed_at_unix_ms": observed_at,
            "evaluated_at_unix_ms": evaluation_time,
            "clock_delta_ms": clock_delta_ms,
            "equity": v5_summary.get("equity"),
            "position_count": _document_int(v5_summary.get("position_count")),
            "portfolio_gross_notional": v5_summary.get("portfolio_gross_notional"),
        },
        "budget_summary": deepcopy(v5_result.get("budget_summary")),
        "checks": checks,
        "facts": {
            "snapshot_transition_exact": transition_exact,
            "expected_current_head_matches": current_head_matches,
            "stale_head_rejected_by_external_commitment": current_head_matches,
            "predecessor_admission_authority_preserved_blocked": (
                v5_admission_locked
            ),
            "snapshot_sequence_transition_arithmetic_verified": bool(
                transition_facts.get(
                    "snapshot_sequence_transition_arithmetic_verified"
                )
                is True
            ),
            "snapshot_freshness_window_arithmetic_verified": bool(
                not_too_old and not_too_far_future and evaluation_time_monotonic
            ),
            "snapshot_sequence_continuity_verified": False,
            "snapshot_freshness_verified": False,
            "trusted_evaluation_clock_verified": False,
            "atomic_current_head_persistence_verified": False,
            "snapshot_source_truth_verified": False,
            "caller_equity_input_accepted": False,
            "caller_positions_input_accepted": False,
            "raw_positions_embedded": False,
            "runtime_gate_integrated": False,
            "execution_verified": False,
            "profitability_proven": False,
            "network_accessed": False,
            "runtime_assets_accessed": False,
        },
        "blockers": _blockers(checks),
        "limitations": deepcopy(_LIMITATIONS),
        "authority": _locked_authority(),
    }
    return seal_strict_canonical_document(document, "budget_v6_hash")


def verify_strategy_correlation_cluster_effective_bet_budget_v6(
    document: Any,
    *args: Any,
    expected_budget_v6_hash: Any,
    **kwargs: Any,
) -> bool:
    if not isinstance(document, dict):
        return False
    try:
        expected_hash = _require_sha256(
            expected_budget_v6_hash,
            "expected_budget_v6_hash",
        )
        rebuilt = evaluate_strategy_correlation_cluster_effective_bet_budget_v6(
            *args,
            **kwargs,
        )
    except Exception:
        return False
    return (
        rebuilt.get("budget_v6_hash") == expected_hash
        and strict_json_contract_equal(document, rebuilt)
    )
