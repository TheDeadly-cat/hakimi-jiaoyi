from __future__ import annotations

import math
from typing import Any

from .strict_canonical_json_hash import strict_json_contract_equal
from .strategy_correlation_multiplicity_report import (
    STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_SCHEMA_VERSION,
    verify_strategy_correlation_multiplicity_report_evidence,
)
from .strategy_matrix_protocol import (
    STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION,
)


STRATEGY_CORRELATION_MULTIPLICITY_PUBLIC_SUMMARY_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-public-summary-v1"
)
STRATEGY_CORRELATION_MULTIPLICITY_PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-multiplicity-public-summary-verification-v1"
)
REQUIRED_REPORT_SCHEMA_VERSION = 16
REQUIRED_MATRIX_REPORT_SCHEMA_VERSION = 8
EVIDENCE_SCOPE = "REDACTED_LOCAL_CORRELATION_MULTIPLICITY"
FAMILYWISE_METHOD = "BONFERRONI_TWO_SIDED_95_FWER_CROSS_CLUSTER_V1"
FAMILYWISE_CONFIDENCE_LEVEL = 0.95
FAMILYWISE_ALPHA = 0.05
MATURITY = "DESCRIPTIVE_ONLY"
PERMISSION = "RESEARCH_ONLY"

_PUBLIC_FIELDS = {
    "schema_version",
    "status",
    "decision_status",
    "required_source_schema_version",
    "required_report_schema_version",
    "required_matrix_report_schema_version",
    "evidence_scope",
    "familywise_method",
    "familywise_confidence_level",
    "familywise_alpha",
    "expected_family_size",
    "observed_family_size",
    "per_pair_alpha",
    "gap_category",
    "maturity",
    "permission",
    "external_authenticity_proven",
    "profitability_proven",
    "performance_claim_allowed",
    "parameter_selection_allowed",
    "formal_registry_bound",
    "current_report_schema_bound",
    "requires_current_consumer_activation",
    "current_writer_activation_allowed",
    "current_admission_allowed",
    "paper_authorized",
    "live_order_allowed",
}
_FIXED_PUBLIC_VALUES = {
    "schema_version": (
        STRATEGY_CORRELATION_MULTIPLICITY_PUBLIC_SUMMARY_SCHEMA_VERSION
    ),
    "required_source_schema_version": (
        STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_SCHEMA_VERSION
    ),
    "required_report_schema_version": REQUIRED_REPORT_SCHEMA_VERSION,
    "required_matrix_report_schema_version": REQUIRED_MATRIX_REPORT_SCHEMA_VERSION,
    "evidence_scope": EVIDENCE_SCOPE,
    "familywise_method": FAMILYWISE_METHOD,
    "familywise_confidence_level": FAMILYWISE_CONFIDENCE_LEVEL,
    "familywise_alpha": FAMILYWISE_ALPHA,
    "maturity": MATURITY,
    "permission": PERMISSION,
    "external_authenticity_proven": False,
    "profitability_proven": False,
    "performance_claim_allowed": False,
    "parameter_selection_allowed": False,
    "formal_registry_bound": False,
    "current_report_schema_bound": False,
    "requires_current_consumer_activation": True,
    "current_writer_activation_allowed": False,
    "current_admission_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}
_SOURCE_FIXED_VALUES = {
    "schema_version": (
        STRATEGY_CORRELATION_MULTIPLICITY_REPORT_EVIDENCE_SCHEMA_VERSION
    ),
    "status": "PASS",
    "required_matrix_report_schema_version": REQUIRED_MATRIX_REPORT_SCHEMA_VERSION,
    "formal_registry_bound": False,
    "current_report_schema_bound": False,
    "current_writer_activation_allowed": False,
    "current_admission_allowed": False,
    "parameter_selection_allowed": False,
    "performance_claim_allowed": False,
    "profitability_proven": False,
}


def _native_positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _unknown_summary() -> dict[str, Any]:
    return {
        **_FIXED_PUBLIC_VALUES,
        "status": "UNKNOWN",
        "decision_status": None,
        "expected_family_size": None,
        "observed_family_size": None,
        "per_pair_alpha": None,
        "gap_category": "SOURCE_INVALID",
    }


def _gap_category(source: dict[str, Any]) -> str:
    if source["decision_status"] == "PASS":
        return "NONE_OBSERVED"
    if source["gate_status"] != "PASS":
        return "CORRELATION_GATE_BLOCK"
    if source["uncertainty_status"] != "PASS":
        return "UNCERTAINTY_BLOCK"
    if source["multiplicity_status"] != "PASS":
        return "FAMILY_WISE_MULTIPLICITY_BLOCK"
    return "SOURCE_DECISION_BLOCK"


def _verified_public_source(
    source_evidence: Any,
    *,
    protocol: Any,
    report_schema_version: Any,
) -> dict[str, Any] | None:
    if report_schema_version != REQUIRED_REPORT_SCHEMA_VERSION:
        return None
    if not isinstance(source_evidence, dict) or not isinstance(protocol, dict):
        return None
    if (
        protocol.get("schema_version")
        != STRATEGY_MATRIX_PROTOCOL_MULTIPLICITY_VERSION
    ):
        return None
    verification = verify_strategy_correlation_multiplicity_report_evidence(
        source_evidence,
        protocol=protocol,
    )
    if (
        verification.get("status") != "PASS"
        or verification.get("evidence_status") != "PASS"
    ):
        return None
    if any(
        source_evidence.get(key) != value
        for key, value in _SOURCE_FIXED_VALUES.items()
    ):
        return None
    permissions = source_evidence.get("permissions")
    if (
        not isinstance(permissions, dict)
        or permissions.get("paper_authorized") is not False
        or permissions.get("live_order_allowed") is not False
    ):
        return None
    expected = source_evidence.get("expected_family_size")
    observed = source_evidence.get("observed_family_size")
    if (
        not _native_positive_int(expected)
        or not _native_positive_int(observed)
        or expected != observed
    ):
        return None
    decision_status = source_evidence.get("decision_status")
    gate_status = source_evidence.get("gate_status")
    uncertainty_status = source_evidence.get("uncertainty_status")
    multiplicity_status = source_evidence.get("multiplicity_status")
    if decision_status not in {"PASS", "BLOCK"}:
        return None
    if any(
        status not in {"PASS", "BLOCK"}
        for status in (gate_status, uncertainty_status, multiplicity_status)
    ):
        return None
    all_decisions_pass = all(
        status == "PASS"
        for status in (gate_status, uncertainty_status, multiplicity_status)
    )
    if (decision_status == "PASS") != all_decisions_pass:
        return None
    return {
        "decision_status": decision_status,
        "expected_family_size": expected,
        "observed_family_size": observed,
        "gate_status": gate_status,
        "uncertainty_status": uncertainty_status,
        "multiplicity_status": multiplicity_status,
    }


def build_strategy_correlation_multiplicity_public_summary(
    source_evidence: Any,
    *,
    protocol: Any,
    report_schema_version: Any,
) -> dict[str, Any]:
    source = _verified_public_source(
        source_evidence,
        protocol=protocol,
        report_schema_version=report_schema_version,
    )
    if source is None:
        return _unknown_summary()
    decision_status = str(source["decision_status"])
    expected_family_size = int(source["expected_family_size"])
    return {
        **_FIXED_PUBLIC_VALUES,
        "status": (
            "OBSERVED_NO_FAMILY_WISE_BLOCK"
            if decision_status == "PASS"
            else "OBSERVED_FAMILY_WISE_BLOCK"
        ),
        "decision_status": decision_status,
        "expected_family_size": expected_family_size,
        "observed_family_size": int(source["observed_family_size"]),
        "per_pair_alpha": FAMILYWISE_ALPHA / expected_family_size,
        "gap_category": _gap_category(source),
    }


def verify_strategy_correlation_multiplicity_public_summary(
    document: Any,
    *,
    source_evidence: Any | None = None,
    protocol: Any = None,
    report_schema_version: Any = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(document, dict):
        blockers.append("strategy_correlation_multiplicity_public_summary_type_invalid")
        document = {}
    if set(document) != _PUBLIC_FIELDS:
        blockers.append("strategy_correlation_multiplicity_public_summary_fields_invalid")
    for key, expected in _FIXED_PUBLIC_VALUES.items():
        if not strict_json_contract_equal(document.get(key), expected):
            blockers.append(
                f"strategy_correlation_multiplicity_public_summary_fixed_value:{key}"
            )

    status = document.get("status")
    if status == "UNKNOWN":
        if (
            document.get("decision_status") is not None
            or document.get("expected_family_size") is not None
            or document.get("observed_family_size") is not None
            or document.get("per_pair_alpha") is not None
            or document.get("gap_category") != "SOURCE_INVALID"
        ):
            blockers.append(
                "strategy_correlation_multiplicity_public_summary_unknown_shape_invalid"
            )
    elif status in {
        "OBSERVED_NO_FAMILY_WISE_BLOCK",
        "OBSERVED_FAMILY_WISE_BLOCK",
    }:
        expected = document.get("expected_family_size")
        observed = document.get("observed_family_size")
        per_pair_alpha = document.get("per_pair_alpha")
        if (
            not _native_positive_int(expected)
            or not _native_positive_int(observed)
            or expected != observed
            or type(per_pair_alpha) not in {int, float}
            or not math.isfinite(float(per_pair_alpha))
            or not math.isclose(
                float(per_pair_alpha),
                FAMILYWISE_ALPHA / expected,
                rel_tol=0.0,
                abs_tol=1e-15,
            )
        ):
            blockers.append(
                "strategy_correlation_multiplicity_public_summary_family_invalid"
            )
        decision_status = document.get("decision_status")
        expected_status = (
            "OBSERVED_NO_FAMILY_WISE_BLOCK"
            if decision_status == "PASS"
            else "OBSERVED_FAMILY_WISE_BLOCK"
            if decision_status == "BLOCK"
            else ""
        )
        if status != expected_status:
            blockers.append(
                "strategy_correlation_multiplicity_public_summary_decision_invalid"
            )
        allowed_gaps = (
            {"NONE_OBSERVED"}
            if decision_status == "PASS"
            else {
                "CORRELATION_GATE_BLOCK",
                "UNCERTAINTY_BLOCK",
                "FAMILY_WISE_MULTIPLICITY_BLOCK",
                "SOURCE_DECISION_BLOCK",
            }
        )
        if document.get("gap_category") not in allowed_gaps:
            blockers.append(
                "strategy_correlation_multiplicity_public_summary_gap_invalid"
            )
    else:
        blockers.append("strategy_correlation_multiplicity_public_summary_status_invalid")

    if source_evidence is not None:
        expected_document = build_strategy_correlation_multiplicity_public_summary(
            source_evidence,
            protocol=protocol,
            report_schema_version=report_schema_version,
        )
        if not strict_json_contract_equal(document, expected_document):
            blockers.append(
                "strategy_correlation_multiplicity_public_summary_source_mismatch"
            )
    blockers = list(dict.fromkeys(blockers))
    return {
        "schema_version": (
            STRATEGY_CORRELATION_MULTIPLICITY_PUBLIC_SUMMARY_VERIFICATION_SCHEMA_VERSION
        ),
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "current_report_schema_bound": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
