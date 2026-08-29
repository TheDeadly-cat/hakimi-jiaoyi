from __future__ import annotations

from typing import Any

from exchange_terminal.services.strategy_correlation_uncertainty_audit import (
    verify_strategy_correlation_uncertainty_audit,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    strict_json_contract_equal,
)


STRATEGY_CORRELATION_UNCERTAINTY_PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-public-summary-v1"
)
STRATEGY_CORRELATION_UNCERTAINTY_PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-public-summary-verification-v1"
)
REQUIRED_SOURCE_SCHEMA_VERSION = "strategy-correlation-uncertainty-audit-v2"
EVIDENCE_SCOPE = "REDACTED_LOCAL_CORRELATION_UNCERTAINTY"
UNCERTAINTY_POLICY = "FISHER_Z_95_WITH_LAG1_EFFECTIVE_N_DESCRIPTIVE_V1"
EFFECTIVE_SAMPLE_METHOD = "LAG1_AUTOCORRELATION_PRODUCT_CLIPPED_V1"
LOOKBACK_OBSERVATIONS = 60
REQUIRED_PRICE_ROWS = 61
MINIMUM_PAIR_OVERLAP = 40
MINIMUM_EFFECTIVE_OBSERVATIONS = 12.0
CONFIDENCE_LEVEL = 0.95
ABSOLUTE_PEARSON_THRESHOLD = 0.75
MATURITY = "DESCRIPTIVE_ONLY"
PERMISSION = "RESEARCH_ONLY"

_COUNT_FIELDS = (
    "pair_count",
    "cross_cluster_pair_count",
    "confirmed_high_cross_cluster_count",
    "ambiguous_cross_cluster_count",
    "insufficient_effective_sample_pair_count",
)
_PUBLIC_FIELDS = {
    "schema_version",
    "status",
    "required_source_schema_version",
    "evidence_scope",
    "uncertainty_policy",
    "effective_sample_method",
    "lookback_observations",
    "required_price_rows",
    "minimum_pair_overlap",
    "minimum_effective_observations",
    "confidence_level",
    "absolute_pearson_threshold",
    *_COUNT_FIELDS,
    "gap_category",
    "maturity",
    "permission",
    "external_authenticity_proven",
    "profitability_proven",
    "performance_claim_allowed",
    "parameter_selection_allowed",
    "requires_new_report_schema",
    "current_writer_activation_allowed",
    "current_admission_allowed",
    "paper_authorized",
    "live_order_allowed",
}
_FIXED_PUBLIC_VALUES = {
    "schema_version": STRATEGY_CORRELATION_UNCERTAINTY_PUBLIC_SUMMARY_SCHEMA_VERSION,
    "required_source_schema_version": REQUIRED_SOURCE_SCHEMA_VERSION,
    "evidence_scope": EVIDENCE_SCOPE,
    "uncertainty_policy": UNCERTAINTY_POLICY,
    "effective_sample_method": EFFECTIVE_SAMPLE_METHOD,
    "lookback_observations": LOOKBACK_OBSERVATIONS,
    "required_price_rows": REQUIRED_PRICE_ROWS,
    "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
    "minimum_effective_observations": MINIMUM_EFFECTIVE_OBSERVATIONS,
    "confidence_level": CONFIDENCE_LEVEL,
    "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
    "maturity": MATURITY,
    "permission": PERMISSION,
    "external_authenticity_proven": False,
    "profitability_proven": False,
    "performance_claim_allowed": False,
    "parameter_selection_allowed": False,
    "requires_new_report_schema": True,
    "current_writer_activation_allowed": False,
    "current_admission_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}
_SOURCE_FIXED_VALUES = {
    "schema_version": REQUIRED_SOURCE_SCHEMA_VERSION,
    "uncertainty_policy": UNCERTAINTY_POLICY,
    "effective_sample_method": EFFECTIVE_SAMPLE_METHOD,
    "lookback_observations": LOOKBACK_OBSERVATIONS,
    "required_price_rows": REQUIRED_PRICE_ROWS,
    "minimum_pair_overlap": MINIMUM_PAIR_OVERLAP,
    "minimum_effective_observations": MINIMUM_EFFECTIVE_OBSERVATIONS,
    "confidence_level": CONFIDENCE_LEVEL,
    "absolute_pearson_threshold": ABSOLUTE_PEARSON_THRESHOLD,
    "external_authenticity_proven": False,
    "profitability_proven": False,
    "performance_claim_allowed": False,
    "parameter_selection_allowed": False,
    "requires_new_report_schema": True,
    "current_writer_activation_allowed": False,
    "current_admission_allowed": False,
}


def _native_nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _unknown_summary() -> dict[str, Any]:
    return {
        **_FIXED_PUBLIC_VALUES,
        "status": "UNKNOWN",
        **{field: None for field in _COUNT_FIELDS},
        "gap_category": "SOURCE_INVALID",
    }


def _gap_category(
    source_status: str,
    *,
    confirmed_high: int,
    ambiguous: int,
    insufficient: int,
) -> str:
    categories = []
    if confirmed_high:
        categories.append("CROSS_CLUSTER_CONFIRMED_HIGH")
    if ambiguous:
        categories.append("CROSS_CLUSTER_AMBIGUOUS")
    if insufficient:
        categories.append("EFFECTIVE_SAMPLE_INSUFFICIENT")
    if len(categories) > 1:
        return "MULTIPLE_CROSS_CLUSTER_UNCERTAINTY_GAPS"
    if categories:
        return categories[0]
    if source_status == "BLOCK":
        return "SOURCE_EVIDENCE_BLOCK"
    return "NONE_OBSERVED"


def _verified_public_source(source_audit: Any) -> dict[str, Any] | None:
    verification = verify_strategy_correlation_uncertainty_audit(source_audit)
    if verification.get("status") != "PASS" or not isinstance(source_audit, dict):
        return None
    if any(source_audit.get(key) != value for key, value in _SOURCE_FIXED_VALUES.items()):
        return None
    permissions = source_audit.get("permissions")
    if (
        not isinstance(permissions, dict)
        or permissions.get("paper_authorized") is not False
        or permissions.get("live_order_allowed") is not False
    ):
        return None
    source_status = source_audit.get("status")
    if source_status not in {"PASS", "BLOCK"}:
        return None
    counts = {field: source_audit.get(field) for field in _COUNT_FIELDS}
    if not all(_native_nonnegative_int(value) for value in counts.values()):
        return None
    if counts["cross_cluster_pair_count"] > counts["pair_count"]:
        return None
    blocking_total = (
        counts["confirmed_high_cross_cluster_count"]
        + counts["ambiguous_cross_cluster_count"]
        + counts["insufficient_effective_sample_pair_count"]
    )
    if blocking_total > counts["cross_cluster_pair_count"]:
        return None
    if source_status == "PASS" and blocking_total:
        return None
    return {"source_status": source_status, **counts}


def build_strategy_correlation_uncertainty_public_summary(
    source_audit: Any,
) -> dict[str, Any]:
    source = _verified_public_source(source_audit)
    if source is None:
        return _unknown_summary()
    source_status = str(source["source_status"])
    return {
        **_FIXED_PUBLIC_VALUES,
        "status": (
            "OBSERVED_NO_UNCERTAINTY_BLOCK"
            if source_status == "PASS"
            else "OBSERVED_UNCERTAINTY_BLOCK"
        ),
        **{field: source[field] for field in _COUNT_FIELDS},
        "gap_category": _gap_category(
            source_status,
            confirmed_high=source["confirmed_high_cross_cluster_count"],
            ambiguous=source["ambiguous_cross_cluster_count"],
            insufficient=source["insufficient_effective_sample_pair_count"],
        ),
    }


def verify_strategy_correlation_uncertainty_public_summary(
    document: Any,
    *,
    source_audit: Any | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(document, dict):
        blockers.append("strategy_correlation_uncertainty_public_summary_type_invalid")
        document = {}
    if set(document) != _PUBLIC_FIELDS:
        blockers.append("strategy_correlation_uncertainty_public_summary_fields_invalid")
    for key, expected in _FIXED_PUBLIC_VALUES.items():
        if not strict_json_contract_equal(document.get(key), expected):
            blockers.append(
                f"strategy_correlation_uncertainty_public_summary_fixed_value:{key}"
            )

    status = document.get("status")
    gap_category = document.get("gap_category")
    if status == "UNKNOWN":
        if gap_category != "SOURCE_INVALID":
            blockers.append(
                "strategy_correlation_uncertainty_public_summary_unknown_gap_invalid"
            )
        if any(document.get(field) is not None for field in _COUNT_FIELDS):
            blockers.append(
                "strategy_correlation_uncertainty_public_summary_unknown_counts_invalid"
            )
    elif status in {
        "OBSERVED_NO_UNCERTAINTY_BLOCK",
        "OBSERVED_UNCERTAINTY_BLOCK",
    }:
        counts = {field: document.get(field) for field in _COUNT_FIELDS}
        if not all(_native_nonnegative_int(value) for value in counts.values()):
            blockers.append(
                "strategy_correlation_uncertainty_public_summary_counts_invalid"
            )
        else:
            if counts["cross_cluster_pair_count"] > counts["pair_count"]:
                blockers.append(
                    "strategy_correlation_uncertainty_public_summary_pair_counts_invalid"
                )
            blocking_total = (
                counts["confirmed_high_cross_cluster_count"]
                + counts["ambiguous_cross_cluster_count"]
                + counts["insufficient_effective_sample_pair_count"]
            )
            if blocking_total > counts["cross_cluster_pair_count"]:
                blockers.append(
                    "strategy_correlation_uncertainty_public_summary_block_counts_invalid"
                )
            expected_gap = _gap_category(
                "PASS" if status == "OBSERVED_NO_UNCERTAINTY_BLOCK" else "BLOCK",
                confirmed_high=counts["confirmed_high_cross_cluster_count"],
                ambiguous=counts["ambiguous_cross_cluster_count"],
                insufficient=counts["insufficient_effective_sample_pair_count"],
            )
            if gap_category != expected_gap:
                blockers.append(
                    "strategy_correlation_uncertainty_public_summary_gap_invalid"
                )
            if status == "OBSERVED_NO_UNCERTAINTY_BLOCK" and blocking_total:
                blockers.append(
                    "strategy_correlation_uncertainty_public_summary_clear_status_invalid"
                )
    else:
        blockers.append("strategy_correlation_uncertainty_public_summary_status_invalid")

    if source_audit is not None:
        expected = build_strategy_correlation_uncertainty_public_summary(source_audit)
        if not strict_json_contract_equal(document, expected):
            blockers.append(
                "strategy_correlation_uncertainty_public_summary_source_mismatch"
            )
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": (
            STRATEGY_CORRELATION_UNCERTAINTY_PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION
        ),
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
