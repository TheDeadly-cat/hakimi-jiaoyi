from __future__ import annotations

import re
from typing import Any

from exchange_terminal.services.strategy_correlation_cross_lag_factor_conditional_diagnostic import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
    strict_sha256,
)


REGISTRATION_SCHEMA = (
    "strategy-correlation-cross-lag-two-view-multiplicity-registration-candidate-v1"
)
STATIC_FINGERPRINT = "20260822-cross-lag-two-view-multiplicity-registration-1"
CORRECTION_METHOD = "BONFERRONI_TWO_SIDED_FWER_RAW_RESIDUAL_V1"
FAMILY_ALPHA = "0.05"
DEPENDENCE_THRESHOLD = "0.75"
VIEWS = ("RAW", "RESIDUAL")
LAGS = (-2, -1, 1, 2)
MIN_IDENTITY_COUNT = 2
MAX_IDENTITY_COUNT = 64
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


def _authority() -> dict[str, bool]:
    return {
        "candidate_activation_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "global_independence_proven": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "profitability_claim_allowed": False,
        "registration_timing_attested": False,
    }


def _facts(*, built: bool) -> dict[str, bool]:
    return {
        "global_two_view_family_registered": built is True,
        "registration_built_from_pre_evaluation_inputs": built is True,
        "registration_timing_attested": False,
    }


def _unknown() -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "authority": _authority(),
            "blockers": ["TWO_VIEW_REGISTRATION_INVALID"],
            "correction_method": CORRECTION_METHOD,
            "cross_stratum_pair_count": None,
            "dependence_threshold": DEPENDENCE_THRESHOLD,
            "facts": _facts(built=False),
            "family_alpha": FAMILY_ALPHA,
            "global_test_count": None,
            "identity_order_hash": None,
            "lag_count": len(LAGS),
            "lags": list(LAGS),
            "maturity_state": "UNKNOWN",
            "per_view_test_count": None,
            "schema_version": REGISTRATION_SCHEMA,
            "source_state": "UNKNOWN",
            "static_fingerprint": STATIC_FINGERPRINT,
            "stratum_assignment_hash": None,
            "view_count": len(VIEWS),
            "views": list(VIEWS),
        },
        "registration_hash",
    )


def _identifier(value: Any) -> bool:
    return type(value) is str and value.isascii() and _IDENTIFIER.fullmatch(value) is not None


def _normalize_strata(value: Any) -> dict[str, str] | None:
    if type(value) is not dict:
        return None
    if not (MIN_IDENTITY_COUNT <= len(value) <= MAX_IDENTITY_COUNT):
        return None
    normalized: dict[str, str] = {}
    for identity in sorted(value):
        stratum = value.get(identity)
        if not _identifier(identity) or not _identifier(stratum):
            return None
        normalized[identity] = stratum
    if len(set(normalized.values())) < 2:
        return None
    return normalized


def _cross_stratum_pair_count(strata: dict[str, str]) -> int:
    identities = list(strata)
    return sum(
        1
        for left_index, left in enumerate(identities)
        for right in identities[left_index + 1 :]
        if strata[left] != strata[right]
    )


def build_strategy_correlation_cross_lag_two_view_multiplicity_registration(
    preregistered_strata: Any,
    *,
    expected_stratum_assignment_hash: Any,
) -> dict[str, Any]:
    try:
        strata = _normalize_strata(preregistered_strata)
        if strata is None:
            return _unknown()
        if not strict_sha256(expected_stratum_assignment_hash):
            return _unknown()
        stratum_assignment_hash = strict_canonical_hash(strata)
        if stratum_assignment_hash != expected_stratum_assignment_hash:
            return _unknown()
        pair_count = _cross_stratum_pair_count(strata)
        if pair_count < 1:
            return _unknown()
        per_view_test_count = pair_count * len(LAGS)
        global_test_count = per_view_test_count * len(VIEWS)
        return seal_strict_canonical_document(
            {
                "authority": _authority(),
                "blockers": [
                    "REGISTRATION_TIMING_UNATTESTED",
                    "TWO_VIEW_GATE_NOT_ACTIVATED",
                ],
                "correction_method": CORRECTION_METHOD,
                "cross_stratum_pair_count": pair_count,
                "dependence_threshold": DEPENDENCE_THRESHOLD,
                "facts": _facts(built=True),
                "family_alpha": FAMILY_ALPHA,
                "global_test_count": global_test_count,
                "identity_order_hash": strict_canonical_hash(list(strata)),
                "lag_count": len(LAGS),
                "lags": list(LAGS),
                "maturity_state": "CANDIDATE_REGISTERED_NOT_TIME_ATTESTED",
                "per_view_test_count": per_view_test_count,
                "schema_version": REGISTRATION_SCHEMA,
                "source_state": "REGISTERED",
                "static_fingerprint": STATIC_FINGERPRINT,
                "stratum_assignment_hash": stratum_assignment_hash,
                "view_count": len(VIEWS),
                "views": list(VIEWS),
            },
            "registration_hash",
        )
    except Exception:
        return _unknown()


def verify_strategy_correlation_cross_lag_two_view_multiplicity_registration(
    document: Any,
    preregistered_strata: Any,
    *,
    expected_stratum_assignment_hash: Any,
    expected_registration_hash: Any,
) -> bool:
    try:
        if type(document) is not dict:
            return False
        if not strict_sha256(expected_registration_hash):
            return False
        if document.get("registration_hash") != expected_registration_hash:
            return False
        expected = build_strategy_correlation_cross_lag_two_view_multiplicity_registration(
            preregistered_strata,
            expected_stratum_assignment_hash=expected_stratum_assignment_hash,
        )
        return strict_json_contract_equal(document, expected)
    except Exception:
        return False
