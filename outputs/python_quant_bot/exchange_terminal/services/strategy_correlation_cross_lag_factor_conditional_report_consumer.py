from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
    strict_sha256,
    verify_strategy_correlation_cross_lag_factor_conditional_diagnostic as _verify_v1,
)
from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 import (
    DIAGNOSTIC_SCHEMA as SOURCE_SCHEMA,
    REPORT_CONSUMER_SCHEMA as VERIFICATION_SCHEMA,
    STABLE_REPORT_BLOCKER,
    STATIC_FINGERPRINT as SOURCE_STATIC_FINGERPRINT,
    V1_DYNAMIC_BLOCKER,
    V1_SCHEMA,
    V1_STATIC_FINGERPRINT,
    verify_strategy_correlation_cross_lag_factor_conditional_diagnostic_v2 as _verify_v2,
)


STATIC_FINGERPRINT = "20260822-cross-lag-factor-conditional-report-consumer-1"

_STATE_MAP = {
    "NO_CONDITIONAL_DEPENDENCE_DETECTED": (
        "OBSERVED_NO_CONDITIONAL_DEPENDENCE",
        "NO_CONDITIONAL_DEPENDENCE_OBSERVED",
        ("PASS", "PASS"),
    ),
    "COMMON_FACTOR_MEDIATED_CANDIDATE": (
        "OBSERVED_COMMON_FACTOR_MEDIATED_CANDIDATE",
        "COMMON_FACTOR_MEDIATION_CANDIDATE",
        ("BLOCK", "PASS"),
    ),
    "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED": (
        "OBSERVED_RESIDUAL_CROSS_LAG_DEPENDENCE",
        "RESIDUAL_CROSS_LAG_DEPENDENCE_OBSERVED",
        ("BLOCK", "BLOCK"),
    ),
    "SUPPRESSION_OR_FACTOR_MODEL_INSTABILITY": (
        "OBSERVED_SUPPRESSION_OR_MODEL_INSTABILITY",
        "FACTOR_MODEL_INSTABILITY_OBSERVED",
        ("PASS", "BLOCK"),
    ),
}

_EVALUATION_KEYS = {
    "cross_stratum_pair_count",
    "dependent_test_count",
    "evaluation_hash",
    "gate_decision",
    "gate_reason",
    "lag_test_count",
    "max_adjusted_absolute_lower",
    "observation_count",
    "schema_version",
    "static_fingerprint",
}


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "common_factor_causality_proven": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "factor_calibration_attested": False,
        "formal_factor_registration_bound": False,
        "global_two_view_multiplicity_registered": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "raw_independence_proven": False,
        "report_consumer_activated": False,
        "report_mounted": False,
        "residual_independence_proven": False,
    }


def _facts(*, source_verified: bool, source_facts: Any = None) -> dict[str, bool]:
    facts = source_facts if type(source_facts) is dict else {}
    return {
        "calibration_receipt_attested": (
            facts.get("calibration_receipt_attested") is True
        ),
        "global_two_view_multiplicity_registered": (
            facts.get("global_two_view_multiplicity_registered") is True
        ),
        "raw_block_relaxed": facts.get("raw_block_relaxed") is True,
        "raw_c0_verified": facts.get("raw_c0_verified") is True,
        "residual_c0_verified": facts.get("residual_c0_verified") is True,
        "source_diagnostic_verified": source_verified is True,
    }


def _unknown(
    source_state: str,
    blocker: str,
    *,
    source_schema_version: str | None = None,
    source_static_fingerprint: str | None = None,
    source_diagnostic_hash: str | None = None,
    source_v1_diagnostic_hash: str | None = None,
    source_verified: bool = False,
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": [blocker],
            "diagnostic_reason": blocker,
            "diagnostic_state": "UNKNOWN",
            "facts": _facts(source_verified=source_verified),
            "gap_state": blocker,
            "maturity_state": "UNKNOWN",
            "permission_state": "LOCKED",
            "raw_evaluation": None,
            "report_state": "UNKNOWN",
            "residual_evaluation": None,
            "schema_version": VERIFICATION_SCHEMA,
            "source_diagnostic_hash": source_diagnostic_hash,
            "source_factor_observations_hash": None,
            "source_identity_order_hash": None,
            "source_raw_evaluation_hash": None,
            "source_registration_hash": None,
            "source_report_contract": None,
            "source_residual_evaluation_hash": None,
            "source_residual_input_hash": None,
            "source_schema_version": source_schema_version,
            "source_state": source_state,
            "source_static_fingerprint": source_static_fingerprint,
            "source_v1_diagnostic_hash": source_v1_diagnostic_hash,
            "static_fingerprint": STATIC_FINGERPRINT,
        },
        "verification_hash",
    )


def _evaluation_summary(value: Any) -> dict[str, Any] | None:
    if type(value) is not dict or set(value) != _EVALUATION_KEYS:
        return None
    return {key: value[key] for key in sorted(_EVALUATION_KEYS)}


def _source_authority_is_locked(value: Any) -> bool:
    if type(value) is not dict:
        return False
    if value.get("descriptive_only") is not True:
        return False
    return all(
        item is False
        for key, item in value.items()
        if key != "descriptive_only"
    )


def _observed(source: dict[str, Any]) -> dict[str, Any] | None:
    state = source.get("diagnostic_state")
    state_contract = _STATE_MAP.get(state)
    if state_contract is None:
        return None
    report_state, gap_state, decisions = state_contract
    raw = _evaluation_summary(source.get("raw_evaluation"))
    residual = _evaluation_summary(source.get("residual_evaluation"))
    if raw is None or residual is None:
        return None
    if (raw.get("gate_decision"), residual.get("gate_decision")) != decisions:
        return None
    if source.get("source_state") != "OBSERVED":
        return None
    if source.get("maturity_state") != "CANDIDATE_RESIDUALIZED_NOT_FORMAL":
        return None
    if source.get("report_contract") != {
        "activation_state": "UNMOUNTED",
        "schema_version": VERIFICATION_SCHEMA,
    }:
        return None
    blockers = source.get("blockers")
    if type(blockers) is not list or any(type(item) is not str for item in blockers):
        return None
    if blockers.count(STABLE_REPORT_BLOCKER) != 1:
        return None
    if V1_DYNAMIC_BLOCKER in blockers:
        return None
    if not _source_authority_is_locked(source.get("authority")):
        return None
    source_facts = source.get("facts")
    if type(source_facts) is not dict:
        return None
    if source_facts.get("raw_block_relaxed") is not False:
        return None
    if source_facts.get("raw_c0_verified") is not True:
        return None
    if source_facts.get("residual_c0_verified") is not True:
        return None
    hashes = {
        "source_diagnostic_hash": source.get("diagnostic_hash"),
        "source_factor_observations_hash": source.get("factor_observations_hash"),
        "source_identity_order_hash": source.get("identity_order_hash"),
        "source_raw_evaluation_hash": raw.get("evaluation_hash"),
        "source_registration_hash": source.get("registration_hash"),
        "source_residual_evaluation_hash": residual.get("evaluation_hash"),
        "source_residual_input_hash": source.get("residual_input_hash"),
        "source_v1_diagnostic_hash": source.get("source_v1_diagnostic_hash"),
    }
    if any(not strict_sha256(value) for value in hashes.values()):
        return None

    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": list(blockers),
            "diagnostic_reason": source.get("diagnostic_reason"),
            "diagnostic_state": state,
            "facts": _facts(source_verified=True, source_facts=source_facts),
            "gap_state": gap_state,
            "maturity_state": source.get("maturity_state"),
            "permission_state": "LOCKED",
            "raw_evaluation": raw,
            "report_state": report_state,
            "residual_evaluation": residual,
            "schema_version": VERIFICATION_SCHEMA,
            **hashes,
            "source_report_contract": dict(source["report_contract"]),
            "source_schema_version": SOURCE_SCHEMA,
            "source_state": "OBSERVED",
            "source_static_fingerprint": SOURCE_STATIC_FINGERPRINT,
            "static_fingerprint": STATIC_FINGERPRINT,
        },
        "verification_hash",
    )


def consume_strategy_correlation_cross_lag_factor_conditional_diagnostic(
    diagnostic: Any,
    *,
    preregistered_strata: Any,
    aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
    expected_factor_observations_hash: Any,
    expected_diagnostic_hash: Any,
) -> dict[str, Any]:
    try:
        if diagnostic is None:
            return _unknown("MISSING", "F0_V2_DIAGNOSTIC_MISSING")
        if type(diagnostic) is not dict:
            return _unknown("INVALID", "F0_V2_DIAGNOSTIC_INVALID")

        schema = diagnostic.get("schema_version")
        if schema == V1_SCHEMA:
            source_hash = diagnostic.get("diagnostic_hash")
            if (
                strict_sha256(expected_diagnostic_hash)
                and source_hash == expected_diagnostic_hash
                and diagnostic.get("static_fingerprint") == V1_STATIC_FINGERPRINT
                and _verify_v1(
                    diagnostic,
                    preregistered_strata,
                    aligned_observations,
                    residualization_registration,
                    factor_observations,
                    expected_stratum_assignment_hash=expected_stratum_assignment_hash,
                    expected_registration_hash=expected_registration_hash,
                    expected_factor_observations_hash=expected_factor_observations_hash,
                )
            ):
                return _unknown(
                    "UNSUPPORTED",
                    "F0_V1_PRECONSUMER_CONTRACT",
                    source_schema_version=V1_SCHEMA,
                    source_static_fingerprint=V1_STATIC_FINGERPRINT,
                    source_diagnostic_hash=source_hash,
                    source_v1_diagnostic_hash=source_hash,
                    source_verified=True,
                )
            return _unknown("INVALID", "F0_V2_DIAGNOSTIC_INVALID")

        if schema != SOURCE_SCHEMA:
            return _unknown("INVALID", "F0_V2_DIAGNOSTIC_INVALID")
        if not strict_sha256(expected_diagnostic_hash):
            return _unknown("INVALID", "F0_V2_DIAGNOSTIC_INVALID")
        if diagnostic.get("diagnostic_hash") != expected_diagnostic_hash:
            return _unknown("INVALID", "F0_V2_DIAGNOSTIC_INVALID")
        if not _verify_v2(
            diagnostic,
            preregistered_strata,
            aligned_observations,
            residualization_registration,
            factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_diagnostic_hash=expected_diagnostic_hash,
        ):
            return _unknown("INVALID", "F0_V2_DIAGNOSTIC_INVALID")
        if diagnostic.get("source_state") != "OBSERVED":
            return _unknown("INVALID", "F0_V2_DIAGNOSTIC_INVALID")
        observed = _observed(diagnostic)
        return observed if observed is not None else _unknown(
            "INVALID", "F0_V2_DIAGNOSTIC_INVALID"
        )
    except Exception:
        return _unknown("INVALID", "F0_V2_DIAGNOSTIC_INVALID")


def verify_strategy_correlation_cross_lag_factor_conditional_consumer_receipt(
    document: Any,
    diagnostic: Any,
    *,
    preregistered_strata: Any,
    aligned_observations: Any,
    residualization_registration: Any,
    factor_observations: Any,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
    expected_factor_observations_hash: Any,
    expected_diagnostic_hash: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        if not strict_sha256(document.get("verification_hash")):
            return False
        expected = consume_strategy_correlation_cross_lag_factor_conditional_diagnostic(
            diagnostic,
            preregistered_strata=preregistered_strata,
            aligned_observations=aligned_observations,
            residualization_registration=residualization_registration,
            factor_observations=factor_observations,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
            expected_registration_hash=expected_registration_hash,
            expected_factor_observations_hash=expected_factor_observations_hash,
            expected_diagnostic_hash=expected_diagnostic_hash,
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
