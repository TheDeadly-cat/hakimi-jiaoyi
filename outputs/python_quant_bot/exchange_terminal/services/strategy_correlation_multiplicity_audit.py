from __future__ import annotations

import math
from copy import deepcopy
from statistics import NormalDist
from typing import Any

from exchange_terminal.services.execution_authority import authority_violations
from exchange_terminal.services.canonical_json_hash import canonical_hash
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)
from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    verify_strategy_correlation_uncertainty_audit,
)


STRATEGY_CORRELATION_MULTIPLICITY_POLICY_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-policy-v1"
)
STRATEGY_CORRELATION_MULTIPLICITY_AUDIT_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-audit-v1"
)
STRATEGY_CORRELATION_MULTIPLICITY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-verification-v1"
)
SOURCE_AUDIT_SCHEMA_VERSION = "strategy-correlation-uncertainty-audit-v2"
CORRECTION_METHOD = "BONFERRONI_TWO_SIDED_FWER_V1"
FAMILY_SCOPE = "CROSS_CLUSTER_PAIRS_ONLY"
FAMILYWISE_CONFIDENCE_LEVEL = 0.95
ABSOLUTE_PEARSON_THRESHOLD = 0.75
MINIMUM_EFFECTIVE_OBSERVATIONS = 12.0

_PAIR_SOURCE_FIELDS = {
    "left_symbol",
    "right_symbol",
    "left_cluster_id",
    "right_cluster_id",
    "correlation",
    "cross_cluster",
    "effective_observations",
    "overlap_observations",
}


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _native_nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _rounded(value: float) -> float:
    return round(float(value), 12)


def build_strategy_correlation_multiplicity_policy() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": STRATEGY_CORRELATION_MULTIPLICITY_POLICY_SCHEMA_VERSION,
        "source_audit_schema_version": SOURCE_AUDIT_SCHEMA_VERSION,
        "target_audit_schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_AUDIT_SCHEMA_VERSION
        ),
        "correction_method": CORRECTION_METHOD,
        "family_scope": FAMILY_SCOPE,
        "familywise_confidence_level": FAMILYWISE_CONFIDENCE_LEVEL,
        "per_pair_alpha_formula": "0.05 / cross_cluster_pair_count",
        "critical_value_formula": "NORMAL_INV_CDF(1 - 0.05 / (2 * family_size))",
        "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
        "minimum_effective_observations": MINIMUM_EFFECTIVE_OBSERVATIONS,
        "confirmed_high_rule": "adjusted_absolute_interval_lower >= 0.75",
        "confirmed_low_rule": "adjusted_absolute_interval_upper < 0.75",
        "ambiguous_action": "BLOCK_AND_REREGISTER",
        "insufficient_effective_sample_action": "BLOCK_AND_REREGISTER",
        "source_block_action": "PRESERVE_BLOCK",
        "descriptive_only": True,
        "requires_new_report_schema": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["policy_hash"] = canonical_hash(payload)
    return payload


def _invalid_source_artifact() -> dict[str, Any]:
    policy = build_strategy_correlation_multiplicity_policy()
    payload: dict[str, Any] = {
        "schema_version": STRATEGY_CORRELATION_MULTIPLICITY_AUDIT_SCHEMA_VERSION,
        "status": "BLOCK",
        "source_status": "INVALID",
        "source_uncertainty_audit": None,
        "source_audit_hash": "",
        "policy": policy,
        "policy_hash": policy["policy_hash"],
        "family_size": 0,
        "per_pair_alpha": None,
        "adjusted_critical_value": None,
        "pair_count": 0,
        "confirmed_high_cross_cluster_count": 0,
        "confirmed_low_cross_cluster_count": 0,
        "ambiguous_cross_cluster_count": 0,
        "insufficient_effective_sample_pair_count": 0,
        "first_blocking_tier": "SOURCE_INVALID",
        "pairs": [],
        "interpretation": (
            "Source uncertainty audit is invalid; multiplicity evidence is unavailable."
        ),
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "requires_new_report_schema": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["audit_hash"] = canonical_hash(payload)
    return payload


def _source_rows(source: dict[str, Any]) -> list[dict[str, Any]] | None:
    if source.get("schema_version") != SOURCE_AUDIT_SCHEMA_VERSION:
        return None
    if source.get("status") not in {"PASS", "BLOCK"}:
        return None
    source_hash = source.get("audit_hash")
    if (
        not isinstance(source_hash, str)
        or len(source_hash) != 64
        or any(char not in "0123456789abcdef" for char in source_hash)
    ):
        return None
    for field in (
        "external_authenticity_proven",
        "profitability_proven",
        "performance_claim_allowed",
        "parameter_selection_allowed",
        "current_writer_activation_allowed",
        "current_admission_allowed",
    ):
        if source.get(field) is not False:
            return None
    permissions = source.get("permissions")
    if (
        not isinstance(permissions, dict)
        or permissions.get("paper_authorized") is not False
        or permissions.get("live_order_allowed") is not False
    ):
        return None
    source_pairs = source.get("pairs")
    if not isinstance(source_pairs, list):
        return None
    cross_count = source.get("cross_cluster_pair_count")
    if not _native_nonnegative_int(cross_count):
        return None
    rows: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    for source_pair in source_pairs:
        if not isinstance(source_pair, dict):
            return None
        if not _PAIR_SOURCE_FIELDS.issubset(source_pair):
            return None
        if source_pair.get("cross_cluster") is not True:
            continue
        left_symbol = source_pair.get("left_symbol")
        right_symbol = source_pair.get("right_symbol")
        left_cluster = source_pair.get("left_cluster_id")
        right_cluster = source_pair.get("right_cluster_id")
        if not all(
            isinstance(value, str) and value
            for value in (left_symbol, right_symbol, left_cluster, right_cluster)
        ):
            return None
        identity = tuple(sorted((left_symbol, right_symbol)))
        if identity in identities:
            return None
        identities.add(identity)
        correlation = _finite_number(source_pair.get("correlation"))
        effective = _finite_number(source_pair.get("effective_observations"))
        overlap = source_pair.get("overlap_observations")
        if (
            correlation is None
            or not -1.0 < correlation < 1.0
            or effective is None
            or effective < 4.0
            or not _native_nonnegative_int(overlap)
        ):
            return None
        rows.append({
            "left_symbol": left_symbol,
            "right_symbol": right_symbol,
            "left_cluster_id": left_cluster,
            "right_cluster_id": right_cluster,
            "correlation": correlation,
            "effective_observations": effective,
            "overlap_observations": overlap,
        })
    if len(rows) != cross_count:
        return None
    rows.sort(key=lambda row: (row["left_symbol"], row["right_symbol"]))
    return rows


def _absolute_interval(lower: float, upper: float) -> tuple[float, float]:
    if lower <= 0.0 <= upper:
        return 0.0, max(abs(lower), abs(upper))
    magnitudes = (abs(lower), abs(upper))
    return min(magnitudes), max(magnitudes)


def _multiplicity_pair(
    row: dict[str, Any],
    *,
    family_size: int,
    critical_value: float,
) -> dict[str, Any]:
    effective = float(row["effective_observations"])
    result: dict[str, Any] = {
        **row,
        "family_size": family_size,
        "adjusted_interval_lower": None,
        "adjusted_interval_upper": None,
        "adjusted_absolute_interval_lower": None,
        "adjusted_absolute_interval_upper": None,
        "classification": "INSUFFICIENT_EFFECTIVE_SAMPLE",
    }
    if effective < MINIMUM_EFFECTIVE_OBSERVATIONS:
        return result
    correlation = float(row["correlation"])
    standard_error = 1.0 / math.sqrt(effective - 3.0)
    fisher_z = math.atanh(correlation)
    lower = math.tanh(fisher_z - critical_value * standard_error)
    upper = math.tanh(fisher_z + critical_value * standard_error)
    absolute_lower, absolute_upper = _absolute_interval(lower, upper)
    if absolute_lower >= ABSOLUTE_PEARSON_THRESHOLD:
        classification = "CONFIRMED_HIGH"
    elif absolute_upper < ABSOLUTE_PEARSON_THRESHOLD:
        classification = "CONFIRMED_LOW"
    else:
        classification = "AMBIGUOUS"
    result.update({
        "adjusted_interval_lower": _rounded(lower),
        "adjusted_interval_upper": _rounded(upper),
        "adjusted_absolute_interval_lower": _rounded(absolute_lower),
        "adjusted_absolute_interval_upper": _rounded(absolute_upper),
        "classification": classification,
    })
    return result


def build_strategy_correlation_multiplicity_audit(
    source_uncertainty_audit: Any,
) -> dict[str, Any]:
    verification = verify_strategy_correlation_uncertainty_audit(
        source_uncertainty_audit
    )
    if (
        verification.get("status") != "PASS"
        or not isinstance(source_uncertainty_audit, dict)
    ):
        return _invalid_source_artifact()
    source_rows = _source_rows(source_uncertainty_audit)
    if source_rows is None:
        return _invalid_source_artifact()

    family_size = len(source_rows)
    if family_size:
        per_pair_alpha = (1.0 - FAMILYWISE_CONFIDENCE_LEVEL) / family_size
        critical_value = NormalDist().inv_cdf(1.0 - per_pair_alpha / 2.0)
        pair_rows = [
            _multiplicity_pair(
                row,
                family_size=family_size,
                critical_value=critical_value,
            )
            for row in source_rows
        ]
    else:
        per_pair_alpha = None
        critical_value = None
        pair_rows = []

    classifications = [row["classification"] for row in pair_rows]
    confirmed_high = classifications.count("CONFIRMED_HIGH")
    confirmed_low = classifications.count("CONFIRMED_LOW")
    ambiguous = classifications.count("AMBIGUOUS")
    insufficient = classifications.count("INSUFFICIENT_EFFECTIVE_SAMPLE")
    source_status = str(source_uncertainty_audit["status"])
    decision_blocked = (
        source_status == "BLOCK"
        or confirmed_high > 0
        or ambiguous > 0
        or insufficient > 0
    )
    if insufficient:
        first_tier = "INSUFFICIENT_EFFECTIVE_SAMPLE"
    elif confirmed_high:
        first_tier = "CONFIRMED_HIGH"
    elif ambiguous:
        first_tier = "AMBIGUOUS"
    elif source_status == "BLOCK":
        first_tier = "SOURCE_AUDIT_BLOCK"
    else:
        first_tier = "NONE"
    policy = build_strategy_correlation_multiplicity_policy()
    payload: dict[str, Any] = {
        "schema_version": STRATEGY_CORRELATION_MULTIPLICITY_AUDIT_SCHEMA_VERSION,
        "status": "BLOCK" if decision_blocked else "PASS",
        "source_status": source_status,
        "source_uncertainty_audit": deepcopy(source_uncertainty_audit),
        "source_audit_hash": source_uncertainty_audit["audit_hash"],
        "policy": policy,
        "policy_hash": policy["policy_hash"],
        "family_size": family_size,
        "per_pair_alpha": (
            _rounded(per_pair_alpha) if per_pair_alpha is not None else None
        ),
        "adjusted_critical_value": (
            _rounded(critical_value) if critical_value is not None else None
        ),
        "pair_count": family_size,
        "confirmed_high_cross_cluster_count": confirmed_high,
        "confirmed_low_cross_cluster_count": confirmed_low,
        "ambiguous_cross_cluster_count": ambiguous,
        "insufficient_effective_sample_pair_count": insufficient,
        "first_blocking_tier": first_tier,
        "pairs": pair_rows,
        "interpretation": (
            "Family-wise adjusted cross-cluster correlation evidence is "
            "descriptive only and cannot authorize parameter selection or trading."
        ),
        "external_authenticity_proven": False,
        "profitability_proven": False,
        "performance_claim_allowed": False,
        "parameter_selection_allowed": False,
        "requires_new_report_schema": True,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": {
            "paper_authorized": False,
            "live_order_allowed": False,
        },
    }
    payload["audit_hash"] = canonical_hash(payload)
    return payload


def verify_strategy_correlation_multiplicity_audit(
    document: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(document, dict):
        blockers.append("strategy_correlation_multiplicity_audit_type_invalid")
        document = {}
    expected = build_strategy_correlation_multiplicity_audit(
        document.get("source_uncertainty_audit")
    )
    if not strict_json_contract_equal(document, expected):
        blockers.append("strategy_correlation_multiplicity_audit_replay_mismatch")
    if authority_violations(document):
        blockers.append("strategy_correlation_multiplicity_audit_authority_violation")
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_VERIFICATION_SCHEMA_VERSION
        ),
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "audit_hash": expected["audit_hash"] if not blockers else "",
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
