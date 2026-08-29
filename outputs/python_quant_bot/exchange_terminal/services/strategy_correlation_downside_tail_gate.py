from __future__ import annotations

import hmac
import math
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import comb
from typing import Any

from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_governance_primitives import (
    strict_nonempty_string,
    strict_sha256,
)
from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
)


REGISTRATION_SCHEMA = "strategy-correlation-downside-tail-preregistration-candidate-v1"
EVALUATION_SCHEMA = "strategy-correlation-downside-tail-gate-candidate-v1"
STATIC_FINGERPRINT = "20260821-preregistered-downside-tail-gate-1"

MIN_IDENTITY_COUNT = 2
MAX_IDENTITY_COUNT = 64
MIN_OBSERVATION_COUNT = 60
MAX_OBSERVATION_COUNT = 2_000
MIN_TAIL_EVENT_COUNT = 12
TAIL_FRACTION_NUMERATOR = 1
TAIL_FRACTION_DENOMINATOR = 5
MIN_OVERLAP_NUMERATOR = 1
MIN_OVERLAP_DENOMINATOR = 2
FAMILY_ALPHA_NUMERATOR = 1
FAMILY_ALPHA_DENOMINATOR = 20

_REGISTRATION_KEYS = {
    "schema_version",
    "static_fingerprint",
    "registration_id",
    "identity_count",
    "stratum_count",
    "identity_set_hash",
    "stratum_assignment_hash",
    "stratum_by_identity",
    "protocol",
    "authority",
    "registration_hash",
}

_AUTHORITY = {
    "descriptive_only": True,
    "independence_proven": False,
    "count_as_independent_allowed": False,
    "formal_preregistration_bound": False,
    "registration_timing_attested": False,
    "profitability_claim_allowed": False,
    "current_admission_allowed": False,
    "current_writer_activation_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}


def _strict_identifier(value: Any) -> bool:
    return (
        strict_nonempty_string(value)
        and value == value.strip()
        and len(value) <= 128
        and all(ord(character) >= 32 for character in value)
    )


def _normalize_strata(stratum_by_identity: Any) -> dict[str, str]:
    if type(stratum_by_identity) is not dict:
        raise ValueError("stratum_by_identity must be a native object")
    if not MIN_IDENTITY_COUNT <= len(stratum_by_identity) <= MAX_IDENTITY_COUNT:
        raise ValueError("identity count is outside the candidate protocol")

    normalized: dict[str, str] = {}
    for identity, stratum in stratum_by_identity.items():
        if not _strict_identifier(identity) or not _strict_identifier(stratum):
            raise ValueError("identity and stratum ids must be strict identifiers")
        normalized[identity] = stratum

    if len(set(normalized.values())) < 2:
        raise ValueError("at least two preregistered strata are required")
    return dict(sorted(normalized.items()))


def _protocol() -> dict[str, Any]:
    return {
        "observation_alignment": "EXACT_SHARED_OBSERVATION_IDS",
        "pair_scope": "CROSS_PREREGISTERED_STRATA_ONLY",
        "tail_selection": "LOWEST_CEILING_FIFTH_BOUNDARY_TIE_BLOCK",
        "tail_fraction": {
            "numerator": TAIL_FRACTION_NUMERATOR,
            "denominator": TAIL_FRACTION_DENOMINATOR,
        },
        "minimum_observation_count": MIN_OBSERVATION_COUNT,
        "maximum_observation_count": MAX_OBSERVATION_COUNT,
        "minimum_tail_event_count": MIN_TAIL_EVENT_COUNT,
        "minimum_overlap_ratio": {
            "numerator": MIN_OVERLAP_NUMERATOR,
            "denominator": MIN_OVERLAP_DENOMINATOR,
        },
        "association_test": "ONE_SIDED_HYPERGEOMETRIC_OVERLAP",
        "multiplicity": "BONFERRONI_ALL_CROSS_STRATUM_PAIRS",
        "family_alpha": {
            "numerator": FAMILY_ALPHA_NUMERATOR,
            "denominator": FAMILY_ALPHA_DENOMINATOR,
        },
        "decision_contract": "BLOCK_ON_UNKNOWN_OR_ANY_SIGNIFICANT_HIGH_OVERLAP",
    }


def build_strategy_correlation_downside_tail_registration(
    *,
    registration_id: Any,
    stratum_by_identity: Any,
) -> dict[str, Any]:
    if not _strict_identifier(registration_id):
        raise ValueError("registration_id must be a strict identifier")
    normalized = _normalize_strata(stratum_by_identity)
    identities = list(normalized)
    document = {
        "schema_version": REGISTRATION_SCHEMA,
        "static_fingerprint": STATIC_FINGERPRINT,
        "registration_id": registration_id,
        "identity_count": len(identities),
        "stratum_count": len(set(normalized.values())),
        "identity_set_hash": _strict_hash(identities),
        "stratum_assignment_hash": _strict_hash(normalized),
        "stratum_by_identity": normalized,
        "protocol": _protocol(),
        "authority": dict(_AUTHORITY),
    }
    return seal_strict_canonical_document(document, "registration_hash")


def _strict_hash(value: Any) -> str:
    from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash

    return strict_canonical_hash(value)


def verify_strategy_correlation_downside_tail_registration(registration: Any) -> bool:
    if type(registration) is not dict or set(registration) != _REGISTRATION_KEYS:
        return False
    if strict_research_authority_invalid(registration):
        return False
    try:
        expected = build_strategy_correlation_downside_tail_registration(
            registration_id=registration.get("registration_id"),
            stratum_by_identity=registration.get("stratum_by_identity"),
        )
    except (TypeError, ValueError):
        return False
    return strict_json_contract_equal(registration, expected)


def _decimal_text(value: Fraction) -> str:
    with localcontext() as context:
        context.prec = 24
        decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
        return format(decimal_value, ".12g")


def _hypergeometric_upper_tail(
    population_count: int,
    left_tail_count: int,
    right_tail_count: int,
    observed_overlap: int,
) -> Fraction:
    denominator = comb(population_count, right_tail_count)
    upper = min(left_tail_count, right_tail_count)
    lower = max(observed_overlap, left_tail_count + right_tail_count - population_count)
    numerator = 0
    for overlap in range(lower, upper + 1):
        remainder = right_tail_count - overlap
        if 0 <= remainder <= population_count - left_tail_count:
            numerator += comb(left_tail_count, overlap) * comb(
                population_count - left_tail_count,
                remainder,
            )
    return Fraction(numerator, denominator)


def _seal_result(document: dict[str, Any]) -> dict[str, Any]:
    return seal_strict_canonical_document(document, "evaluation_hash")


def _unknown_result(
    reason: str,
    *,
    registration_hash: str | None = None,
) -> dict[str, Any]:
    return _seal_result(
        {
            "schema_version": EVALUATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "UNKNOWN",
            "gate_decision": "BLOCK",
            "gate_reason": reason,
            "maturity_state": "NOT_EVALUABLE",
            "registration_hash": registration_hash,
            "identity_set_hash": None,
            "stratum_assignment_hash": None,
            "observation_count": None,
            "tail_event_count": None,
            "cross_stratum_pair_count": None,
            "tested_pair_count": 0,
            "coupled_pair_count": 0,
            "pair_results": [],
            "blockers": [reason],
            "authority": dict(_AUTHORITY),
        }
    )


def evaluate_strategy_correlation_downside_tail_gate(
    registration: Any,
    aligned_observations: Any,
    *,
    expected_registration_hash: Any,
) -> dict[str, Any]:
    if not verify_strategy_correlation_downside_tail_registration(registration):
        return _unknown_result("REGISTRATION_CONTRACT_INVALID")

    registration_hash = registration["registration_hash"]
    if not strict_sha256(expected_registration_hash) or not hmac.compare_digest(
        registration_hash,
        expected_registration_hash,
    ):
        return _unknown_result(
            "EXPECTED_REGISTRATION_HASH_MISMATCH",
            registration_hash=registration_hash,
        )

    if type(aligned_observations) is not list:
        return _unknown_result(
            "ALIGNED_OBSERVATIONS_INVALID",
            registration_hash=registration_hash,
        )

    identities = list(registration["stratum_by_identity"])
    identity_set = set(identities)
    seen_observation_ids: set[str] = set()
    rows: list[tuple[str, dict[str, float]]] = []
    for row in aligned_observations:
        if type(row) is not dict or set(row) != {"observation_id", "returns"}:
            return _unknown_result(
                "OBSERVATION_ROW_CONTRACT_INVALID",
                registration_hash=registration_hash,
            )
        observation_id = row.get("observation_id")
        returns = row.get("returns")
        if not _strict_identifier(observation_id) or observation_id in seen_observation_ids:
            return _unknown_result(
                "OBSERVATION_ID_INVALID_OR_DUPLICATE",
                registration_hash=registration_hash,
            )
        if type(returns) is not dict or set(returns) != identity_set:
            return _unknown_result(
                "OBSERVATION_IDENTITY_SET_MISMATCH",
                registration_hash=registration_hash,
            )

        normalized_returns: dict[str, float] = {}
        for identity in identities:
            value = returns[identity]
            if type(value) not in (int, float):
                return _unknown_result(
                    "RETURN_VALUE_INVALID",
                    registration_hash=registration_hash,
                )
            numeric = float(value)
            if not math.isfinite(numeric):
                return _unknown_result(
                    "RETURN_VALUE_INVALID",
                    registration_hash=registration_hash,
                )
            normalized_returns[identity] = numeric
        seen_observation_ids.add(observation_id)
        rows.append((observation_id, normalized_returns))

    observation_count = len(rows)
    if not MIN_OBSERVATION_COUNT <= observation_count <= MAX_OBSERVATION_COUNT:
        return _unknown_result(
            "OBSERVATION_COUNT_OUTSIDE_PROTOCOL",
            registration_hash=registration_hash,
        )
    rows.sort(key=lambda item: item[0])

    tail_event_count = (
        observation_count * TAIL_FRACTION_NUMERATOR
        + TAIL_FRACTION_DENOMINATOR
        - 1
    ) // TAIL_FRACTION_DENOMINATOR
    if tail_event_count < MIN_TAIL_EVENT_COUNT:
        return _unknown_result(
            "TAIL_EVENT_COUNT_BELOW_PROTOCOL",
            registration_hash=registration_hash,
        )

    tail_events: dict[str, frozenset[str]] = {}
    for identity in identities:
        ranked = sorted(
            ((values[identity], observation_id) for observation_id, values in rows),
            key=lambda item: (item[0], item[1]),
        )
        if (
            tail_event_count < observation_count
            and ranked[tail_event_count - 1][0] == ranked[tail_event_count][0]
        ):
            return _unknown_result(
                "TAIL_BOUNDARY_TIE_AMBIGUOUS",
                registration_hash=registration_hash,
            )
        tail_events[identity] = frozenset(
            observation_id for _, observation_id in ranked[:tail_event_count]
        )

    strata = registration["stratum_by_identity"]
    pairs = [
        (left, right)
        for left, right in combinations(identities, 2)
        if strata[left] != strata[right]
    ]
    if not pairs:
        return _unknown_result(
            "NO_CROSS_STRATUM_PAIR",
            registration_hash=registration_hash,
        )

    family_pair_count = len(pairs)
    family_alpha = Fraction(FAMILY_ALPHA_NUMERATOR, FAMILY_ALPHA_DENOMINATOR)

    @lru_cache(maxsize=None)
    def overlap_p_value(overlap_count: int) -> Fraction:
        return _hypergeometric_upper_tail(
            observation_count,
            tail_event_count,
            tail_event_count,
            overlap_count,
        )

    pair_results: list[dict[str, Any]] = []
    coupled_pair_count = 0
    for left, right in pairs:
        overlap_count = len(tail_events[left] & tail_events[right])
        overlap_ratio = Fraction(overlap_count, tail_event_count)
        raw_p_value = overlap_p_value(overlap_count)
        adjusted_p_value = min(Fraction(1, 1), raw_p_value * family_pair_count)
        high_overlap = (
            overlap_ratio
            >= Fraction(MIN_OVERLAP_NUMERATOR, MIN_OVERLAP_DENOMINATOR)
        )
        family_significant = adjusted_p_value <= family_alpha
        tail_coupled = high_overlap and family_significant
        if tail_coupled:
            coupled_pair_count += 1
        pair_results.append(
            {
                "left_identity": left,
                "right_identity": right,
                "left_stratum": strata[left],
                "right_stratum": strata[right],
                "tail_event_count": tail_event_count,
                "tail_overlap_count": overlap_count,
                "tail_overlap_ratio": _decimal_text(overlap_ratio),
                "raw_p_value": _decimal_text(raw_p_value),
                "family_adjusted_p_value": _decimal_text(adjusted_p_value),
                "high_overlap": high_overlap,
                "family_significant": family_significant,
                "tail_coupled": tail_coupled,
            }
        )

    blocked = coupled_pair_count > 0
    gate_reason = (
        "DOWNSIDE_TAIL_COUPLING_DETECTED"
        if blocked
        else "NO_SIGNIFICANT_HIGH_DOWNSIDE_TAIL_OVERLAP"
    )
    return _seal_result(
        {
            "schema_version": EVALUATION_SCHEMA,
            "static_fingerprint": STATIC_FINGERPRINT,
            "source_state": "OBSERVED",
            "gate_decision": "BLOCK" if blocked else "PASS",
            "gate_reason": gate_reason,
            "maturity_state": "CANDIDATE_EVALUATED_NOT_FORMAL",
            "registration_hash": registration_hash,
            "identity_set_hash": registration["identity_set_hash"],
            "stratum_assignment_hash": registration["stratum_assignment_hash"],
            "observation_count": observation_count,
            "tail_event_count": tail_event_count,
            "cross_stratum_pair_count": family_pair_count,
            "tested_pair_count": len(pair_results),
            "coupled_pair_count": coupled_pair_count,
            "pair_results": pair_results,
            "blockers": [gate_reason] if blocked else [],
            "authority": dict(_AUTHORITY),
        }
    )


_EVALUATION_KEYS = {
    "schema_version",
    "static_fingerprint",
    "source_state",
    "gate_decision",
    "gate_reason",
    "maturity_state",
    "registration_hash",
    "identity_set_hash",
    "stratum_assignment_hash",
    "observation_count",
    "tail_event_count",
    "cross_stratum_pair_count",
    "tested_pair_count",
    "coupled_pair_count",
    "pair_results",
    "blockers",
    "authority",
    "evaluation_hash",
}

_PAIR_RESULT_KEYS = {
    "left_identity",
    "right_identity",
    "left_stratum",
    "right_stratum",
    "tail_event_count",
    "tail_overlap_count",
    "tail_overlap_ratio",
    "raw_p_value",
    "family_adjusted_p_value",
    "high_overlap",
    "family_significant",
    "tail_coupled",
}

_UNKNOWN_REASONS_WITH_VALID_REGISTRATION = {
    "EXPECTED_REGISTRATION_HASH_MISMATCH",
    "ALIGNED_OBSERVATIONS_INVALID",
    "OBSERVATION_ROW_CONTRACT_INVALID",
    "OBSERVATION_ID_INVALID_OR_DUPLICATE",
    "OBSERVATION_IDENTITY_SET_MISMATCH",
    "RETURN_VALUE_INVALID",
    "OBSERVATION_COUNT_OUTSIDE_PROTOCOL",
    "TAIL_EVENT_COUNT_BELOW_PROTOCOL",
    "TAIL_BOUNDARY_TIE_AMBIGUOUS",
    "NO_CROSS_STRATUM_PAIR",
}


def verify_strategy_correlation_downside_tail_evaluation(
    document: Any,
    registration: Any,
    *,
    expected_registration_hash: Any,
    expected_evaluation_hash: Any,
) -> bool:
    if type(document) is not dict or set(document) != _EVALUATION_KEYS:
        return False
    if not verify_strategy_correlation_downside_tail_registration(registration):
        return False
    registration_hash = registration["registration_hash"]
    if not strict_sha256(expected_registration_hash) or not hmac.compare_digest(
        registration_hash,
        expected_registration_hash,
    ):
        return False
    if not strict_sha256(expected_evaluation_hash):
        return False
    if not strict_sha256(document.get("evaluation_hash")) or not hmac.compare_digest(
        document["evaluation_hash"],
        expected_evaluation_hash,
    ):
        return False
    if document.get("schema_version") != EVALUATION_SCHEMA:
        return False
    if document.get("static_fingerprint") != STATIC_FINGERPRINT:
        return False
    if document.get("registration_hash") != registration_hash:
        return False
    if not strict_json_contract_equal(document.get("authority"), _AUTHORITY):
        return False

    if document.get("source_state") == "UNKNOWN":
        reason = document.get("gate_reason")
        if reason not in _UNKNOWN_REASONS_WITH_VALID_REGISTRATION:
            return False
        expected = _unknown_result(reason, registration_hash=registration_hash)
        return strict_json_contract_equal(document, expected)

    if document.get("source_state") != "OBSERVED":
        return False
    if document.get("maturity_state") != "CANDIDATE_EVALUATED_NOT_FORMAL":
        return False
    if document.get("identity_set_hash") != registration["identity_set_hash"]:
        return False
    if document.get("stratum_assignment_hash") != registration["stratum_assignment_hash"]:
        return False

    observation_count = document.get("observation_count")
    tail_event_count = document.get("tail_event_count")
    if type(observation_count) is not int or not (
        MIN_OBSERVATION_COUNT <= observation_count <= MAX_OBSERVATION_COUNT
    ):
        return False
    expected_tail_count = (
        observation_count * TAIL_FRACTION_NUMERATOR
        + TAIL_FRACTION_DENOMINATOR
        - 1
    ) // TAIL_FRACTION_DENOMINATOR
    if type(tail_event_count) is not int or tail_event_count != expected_tail_count:
        return False
    if tail_event_count < MIN_TAIL_EVENT_COUNT:
        return False

    identities = list(registration["stratum_by_identity"])
    strata = registration["stratum_by_identity"]
    expected_pairs = [
        (left, right)
        for left, right in combinations(identities, 2)
        if strata[left] != strata[right]
    ]
    family_pair_count = len(expected_pairs)
    if family_pair_count == 0:
        return False
    if type(document.get("cross_stratum_pair_count")) is not int or document[
        "cross_stratum_pair_count"
    ] != family_pair_count:
        return False
    if type(document.get("tested_pair_count")) is not int or document[
        "tested_pair_count"
    ] != family_pair_count:
        return False
    pair_results = document.get("pair_results")
    if type(pair_results) is not list or len(pair_results) != family_pair_count:
        return False

    family_alpha = Fraction(FAMILY_ALPHA_NUMERATOR, FAMILY_ALPHA_DENOMINATOR)
    coupled_pair_count = 0
    for item, (left, right) in zip(pair_results, expected_pairs):
        if type(item) is not dict or set(item) != _PAIR_RESULT_KEYS:
            return False
        if item.get("left_identity") != left or item.get("right_identity") != right:
            return False
        if item.get("left_stratum") != strata[left] or item.get("right_stratum") != strata[right]:
            return False
        if type(item.get("tail_event_count")) is not int or item[
            "tail_event_count"
        ] != tail_event_count:
            return False
        overlap_count = item.get("tail_overlap_count")
        if type(overlap_count) is not int or not 0 <= overlap_count <= tail_event_count:
            return False

        overlap_ratio = Fraction(overlap_count, tail_event_count)
        raw_p_value = _hypergeometric_upper_tail(
            observation_count,
            tail_event_count,
            tail_event_count,
            overlap_count,
        )
        adjusted_p_value = min(Fraction(1, 1), raw_p_value * family_pair_count)
        high_overlap = overlap_ratio >= Fraction(
            MIN_OVERLAP_NUMERATOR,
            MIN_OVERLAP_DENOMINATOR,
        )
        family_significant = adjusted_p_value <= family_alpha
        tail_coupled = high_overlap and family_significant
        expected_item = {
            "left_identity": left,
            "right_identity": right,
            "left_stratum": strata[left],
            "right_stratum": strata[right],
            "tail_event_count": tail_event_count,
            "tail_overlap_count": overlap_count,
            "tail_overlap_ratio": _decimal_text(overlap_ratio),
            "raw_p_value": _decimal_text(raw_p_value),
            "family_adjusted_p_value": _decimal_text(adjusted_p_value),
            "high_overlap": high_overlap,
            "family_significant": family_significant,
            "tail_coupled": tail_coupled,
        }
        if not strict_json_contract_equal(item, expected_item):
            return False
        if tail_coupled:
            coupled_pair_count += 1

    if type(document.get("coupled_pair_count")) is not int or document[
        "coupled_pair_count"
    ] != coupled_pair_count:
        return False
    blocked = coupled_pair_count > 0
    expected_decision = "BLOCK" if blocked else "PASS"
    expected_reason = (
        "DOWNSIDE_TAIL_COUPLING_DETECTED"
        if blocked
        else "NO_SIGNIFICANT_HIGH_DOWNSIDE_TAIL_OVERLAP"
    )
    if document.get("gate_decision") != expected_decision:
        return False
    if document.get("gate_reason") != expected_reason:
        return False
    if not strict_json_contract_equal(
        document.get("blockers"),
        [expected_reason] if blocked else [],
    ):
        return False

    payload = {key: value for key, value in document.items() if key != "evaluation_hash"}
    expected_seal = seal_strict_canonical_document(payload, "evaluation_hash")
    return strict_json_contract_equal(document, expected_seal)
