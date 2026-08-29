from __future__ import annotations

import re
from typing import Any

from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_longitudinal_coverage_v1 as coverage_contract
from exchange_terminal.services import strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_assertion_replay_checkpoint_persistence_uniqueness_freshness_verifier_v1 as signed_claim_contract
from exchange_terminal.services.strict_canonical_json_hash import seal_strict_canonical_document


SCHEMA_VERSION = (
    "strategy-correlation-cross-lag-factor-calibration-long-horizon-provider-"
    "identity-uniqueness-freshness-presentation-envelope-v1"
)
STATIC_FINGERPRINT = (
    "20261004-cross-lag-factor-calibration-long-horizon-provider-identity-"
    "uniqueness-freshness-presentation-envelope-1"
)
PRESENTATION_STATUS = "UNMOUNTED_CANDIDATE"
POSITIVE_DISPLAY_STATE = "SIGNED_CLAIMS_BOUND_BOUNDED_PREFIX_EXTERNAL_TRUST_GAP"
UNKNOWN_DISPLAY_STATE = "UNKNOWN"
AXIS_ORDER = ("SOURCE", "GAP", "MATURITY", "PERMISSION")

SIGNED_CLAIM_SCHEMA = signed_claim_contract.EVALUATION_SCHEMA
SIGNED_CLAIM_STATIC_FINGERPRINT = signed_claim_contract.STATIC_FINGERPRINT
SIGNED_CLAIM_STATE = signed_claim_contract.VERIFIED_STATUS
COVERAGE_SCHEMA = coverage_contract.EVALUATION_SCHEMA
COVERAGE_STATIC_FINGERPRINT = coverage_contract.STATIC_FINGERPRINT
COVERAGE_STATE = coverage_contract.VERIFIED_STATUS

VERIFIED_BLOCKERS = (
    "EXTERNAL_OCCURRENCE_INDEX_COMPLETENESS_UNPROVEN",
    "EXTERNAL_OCCURRENCE_PROVIDER_TRUST_UNPROVEN",
    "EXTERNAL_TIME_AUTHORITY_UNPROVEN",
    "REFERENCE_CLOCK_CORRECTNESS_UNPROVEN",
    "CHECKPOINTS_OUTSIDE_REGISTERED_WINDOW_UNOBSERVED",
    "FUTURE_REPLAY_ABSENCE_UNPROVEN",
    "GLOBAL_ASSERTION_UNIQUENESS_UNPROVEN",
    "TRADING_AUTHORITY_NOT_GRANTED",
)
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _authority() -> dict[str, bool]:
    return {
        "descriptive_only": True,
        "uniqueness_truth_promotion_allowed": False,
        "freshness_truth_promotion_allowed": False,
        "replay_absence_promotion_allowed": False,
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _facts() -> dict[str, bool]:
    return {
        "result_available": False,
        "signed_claim_evaluation_verified": False,
        "longitudinal_coverage_evaluation_verified": False,
        "complete_scan_claim_verified": False,
        "time_window_claim_verified": False,
        "bounded_prefix_verified": False,
        "external_occurrence_provider_trust_attested": False,
        "external_time_authority_trust_attested": False,
        "assertion_uniqueness_verified": False,
        "freshness_verified": False,
        "replay_absence_verified": False,
        "complete_history_verified": False,
    }


def _summary() -> dict[str, Any]:
    return {
        "replay_registry_id": None,
        "assertion_receipt_hash": None,
        "assertion_leaf_index": None,
        "checkpoint_tree_size": None,
        "coverage_start_tree_size": None,
        "coverage_end_tree_size": None,
        "coverage_evaluation_count": None,
        "maximum_reference_time_gap_ms": None,
        "occurrence_provider_id": None,
        "time_authority_id": None,
        "scan_completed_at_ms_claim": None,
        "reference_time_ms_claim": None,
    }


def _lineage() -> dict[str, Any]:
    return {
        "signed_claim_evaluation_receipt_hash": None,
        "coverage_evaluation_receipt_hash": None,
        "source_evidence_registration_receipt_hash": None,
        "coverage_registration_receipt_hash": None,
        "first_source_evaluation_receipt_hash": None,
        "last_source_evaluation_receipt_hash": None,
        "first_checkpoint_hash": None,
        "last_checkpoint_hash": None,
    }


def _unknown_axes(detail: str) -> list[dict[str, str]]:
    return [
        {
            "axis": axis,
            "state": "UNKNOWN",
            "signal": "UNKNOWN",
            "headline": "Evidence unavailable",
            "detail": detail,
        }
        for axis in AXIS_ORDER
    ]


def _sealed(
    *,
    display_state: str,
    source_signed_claim_schema: str | None,
    source_signed_claim_fingerprint: str | None,
    source_coverage_schema: str | None,
    source_coverage_fingerprint: str | None,
    axes: list[dict[str, str]],
    summary: dict[str, Any],
    lineage: dict[str, Any],
    facts: dict[str, bool],
    blockers: list[str],
) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "schema_version": SCHEMA_VERSION,
            "static_fingerprint": STATIC_FINGERPRINT,
            "presentation_status": PRESENTATION_STATUS,
            "source_signed_claim_schema": source_signed_claim_schema,
            "source_signed_claim_fingerprint": source_signed_claim_fingerprint,
            "source_coverage_schema": source_coverage_schema,
            "source_coverage_fingerprint": source_coverage_fingerprint,
            "display_state": display_state,
            "axis_order": list(AXIS_ORDER),
            "axes": axes,
            "summary": summary,
            "lineage": lineage,
            "facts": facts,
            "authority": _authority(),
            "blockers": blockers,
        },
        "presentation_hash",
    )


def _unknown(reason: str) -> dict[str, Any]:
    detail = "The sealed signed-claim and longitudinal coverage contracts did not verify for presentation."
    return _sealed(
        display_state=UNKNOWN_DISPLAY_STATE,
        source_signed_claim_schema=None,
        source_signed_claim_fingerprint=None,
        source_coverage_schema=None,
        source_coverage_fingerprint=None,
        axes=_unknown_axes(detail),
        summary=_summary(),
        lineage=_lineage(),
        facts=_facts(),
        blockers=[reason],
    )


def _strict_hash(value: Any) -> bool:
    return type(value) is str and _LOWER_SHA256.fullmatch(value) is not None


def _strict_int(value: Any) -> bool:
    return type(value) is int and 0 <= value <= 2**63 - 1


def build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
    signed_claim_evaluation_v1: Any,
    signed_claim_evaluation_inputs: Any,
    longitudinal_coverage_evaluation_v1: Any,
    longitudinal_coverage_evaluation_context: Any,
    *,
    expected_signed_claim_evaluation_hash: Any,
    expected_longitudinal_coverage_evaluation_hash: Any,
) -> dict[str, Any]:
    if not _strict_hash(expected_signed_claim_evaluation_hash):
        return _unknown("EXPECTED_SIGNED_CLAIM_EVALUATION_HASH_INVALID")
    if not _strict_hash(expected_longitudinal_coverage_evaluation_hash):
        return _unknown("EXPECTED_LONGITUDINAL_COVERAGE_EVALUATION_HASH_INVALID")
    if type(signed_claim_evaluation_v1) is not dict or type(signed_claim_evaluation_inputs) is not dict:
        return _unknown("SIGNED_CLAIM_EVALUATION_INPUTS_INVALID")
    if type(longitudinal_coverage_evaluation_v1) is not dict or type(longitudinal_coverage_evaluation_context) is not dict:
        return _unknown("LONGITUDINAL_COVERAGE_EVALUATION_INPUTS_INVALID")
    if signed_claim_evaluation_v1.get("receipt_hash") != expected_signed_claim_evaluation_hash:
        return _unknown("SIGNED_CLAIM_EVALUATION_HASH_MISMATCH")
    if longitudinal_coverage_evaluation_v1.get("receipt_hash") != expected_longitudinal_coverage_evaluation_hash:
        return _unknown("LONGITUDINAL_COVERAGE_EVALUATION_HASH_MISMATCH")
    try:
        signed_claim_verified = signed_claim_contract.verify_provider_identity_assertion_uniqueness_freshness_evaluation_v1(
            signed_claim_evaluation_v1,
            **signed_claim_evaluation_inputs,
        )
    except (KeyError, TypeError, ValueError):
        signed_claim_verified = False
    if not signed_claim_verified or signed_claim_evaluation_v1.get("status") != SIGNED_CLAIM_STATE:
        return _unknown("SIGNED_CLAIM_EVALUATION_UNVERIFIED")
    try:
        coverage_verified = coverage_contract.verify_provider_identity_assertion_uniqueness_freshness_longitudinal_coverage_evaluation_v1(
            longitudinal_coverage_evaluation_v1,
            **longitudinal_coverage_evaluation_context,
        )
    except (KeyError, TypeError, ValueError):
        coverage_verified = False
    if not coverage_verified or longitudinal_coverage_evaluation_v1.get("status") != COVERAGE_STATE:
        return _unknown("LONGITUDINAL_COVERAGE_EVALUATION_UNVERIFIED")
    source_evidence = signed_claim_evaluation_v1.get("evidence")
    source_facts = signed_claim_evaluation_v1.get("facts")
    source_authority = signed_claim_evaluation_v1.get("authority")
    coverage_evidence = longitudinal_coverage_evaluation_v1.get("evidence")
    coverage_facts = longitudinal_coverage_evaluation_v1.get("facts")
    coverage_authority = longitudinal_coverage_evaluation_v1.get("authority")
    if not all(type(value) is dict for value in (source_evidence, source_facts, source_authority, coverage_evidence, coverage_facts, coverage_authority)):
        return _unknown("SOURCE_EVIDENCE_SHAPE_INVALID")
    if any(not _strict_hash(source_evidence.get(field)) for field in ("registration_receipt_hash", "checkpoint_hash", "assertion_receipt_hash")):
        return _unknown("SIGNED_CLAIM_EVIDENCE_HASH_INVALID")
    if any(not _strict_hash(coverage_evidence.get(field)) for field in ("source_evidence_registration_receipt_hash", "coverage_registration_receipt_hash", "first_source_evaluation_receipt_hash", "last_source_evaluation_receipt_hash", "first_checkpoint_hash", "last_checkpoint_hash")):
        return _unknown("COVERAGE_EVIDENCE_HASH_INVALID")
    if any(not _strict_int(source_evidence.get(field)) for field in ("assertion_leaf_index", "checkpoint_tree_size", "scan_completed_at_ms_claim", "reference_time_ms_claim")):
        return _unknown("SIGNED_CLAIM_EVIDENCE_INTEGER_INVALID")
    if any(not _strict_int(coverage_evidence.get(field)) for field in ("assertion_leaf_index", "evaluation_count", "start_tree_size", "end_tree_size", "maximum_observed_reference_time_gap_ms")):
        return _unknown("COVERAGE_EVIDENCE_INTEGER_INVALID")
    bindings = (
        (source_evidence["registration_receipt_hash"], coverage_evidence["source_evidence_registration_receipt_hash"], "SOURCE_REGISTRATION_BINDING_MISMATCH"),
        (signed_claim_evaluation_v1["receipt_hash"], coverage_evidence["last_source_evaluation_receipt_hash"], "LATEST_SIGNED_CLAIM_BINDING_MISMATCH"),
        (source_evidence["checkpoint_hash"], coverage_evidence["last_checkpoint_hash"], "LATEST_CHECKPOINT_BINDING_MISMATCH"),
        (source_evidence.get("replay_registry_id"), coverage_evidence.get("replay_registry_id"), "REPLAY_REGISTRY_BINDING_MISMATCH"),
        (source_evidence["assertion_receipt_hash"], coverage_evidence.get("assertion_receipt_hash"), "ASSERTION_HASH_BINDING_MISMATCH"),
        (source_evidence["assertion_leaf_index"], coverage_evidence["assertion_leaf_index"], "ASSERTION_LEAF_BINDING_MISMATCH"),
        (source_evidence.get("occurrence_provider_id"), coverage_evidence.get("occurrence_provider_id"), "OCCURRENCE_PROVIDER_BINDING_MISMATCH"),
        (source_evidence.get("time_authority_id"), coverage_evidence.get("time_authority_id"), "TIME_AUTHORITY_BINDING_MISMATCH"),
    )
    for left, right, reason in bindings:
        if left != right or type(left) is not type(right):
            return _unknown(reason)
    for field in ("complete_scan_claim_verified", "exactly_one_occurrence_claim_verified", "time_window_claim_verified"):
        if source_facts.get(field) is not True:
            return _unknown("SIGNED_CLAIM_FACTS_INCOMPLETE")
    for field in ("signed_single_occurrence_claim_prefix_verified", "bounded_prefix_only"):
        if coverage_facts.get(field) is not True:
            return _unknown("COVERAGE_PREFIX_FACT_UNVERIFIED")
    for facts in (source_facts, coverage_facts):
        for field in ("assertion_uniqueness_verified", "freshness_verified", "replay_absence_verified", "complete_history_verified"):
            if facts.get(field) is not False:
                return _unknown("SOURCE_TRUTH_PROMOTION_REJECTED")
    if any(value is not False for value in source_authority.values()) or any(value is not False for value in coverage_authority.values()):
        return _unknown("SOURCE_AUTHORITY_PROMOTION_REJECTED")
    if not all(type(source_evidence.get(field)) is str and source_evidence.get(field) for field in ("replay_registry_id", "occurrence_provider_id", "time_authority_id")):
        return _unknown("SIGNED_CLAIM_IDENTITY_INVALID")
    summary = _summary()
    summary.update(
        {
            "replay_registry_id": source_evidence["replay_registry_id"],
            "assertion_receipt_hash": source_evidence["assertion_receipt_hash"],
            "assertion_leaf_index": source_evidence["assertion_leaf_index"],
            "checkpoint_tree_size": source_evidence["checkpoint_tree_size"],
            "coverage_start_tree_size": coverage_evidence["start_tree_size"],
            "coverage_end_tree_size": coverage_evidence["end_tree_size"],
            "coverage_evaluation_count": coverage_evidence["evaluation_count"],
            "maximum_reference_time_gap_ms": coverage_evidence["maximum_observed_reference_time_gap_ms"],
            "occurrence_provider_id": source_evidence["occurrence_provider_id"],
            "time_authority_id": source_evidence["time_authority_id"],
            "scan_completed_at_ms_claim": source_evidence["scan_completed_at_ms_claim"],
            "reference_time_ms_claim": source_evidence["reference_time_ms_claim"],
        }
    )
    lineage = _lineage()
    lineage.update(
        {
            "signed_claim_evaluation_receipt_hash": signed_claim_evaluation_v1["receipt_hash"],
            "coverage_evaluation_receipt_hash": longitudinal_coverage_evaluation_v1["receipt_hash"],
            "source_evidence_registration_receipt_hash": coverage_evidence["source_evidence_registration_receipt_hash"],
            "coverage_registration_receipt_hash": coverage_evidence["coverage_registration_receipt_hash"],
            "first_source_evaluation_receipt_hash": coverage_evidence["first_source_evaluation_receipt_hash"],
            "last_source_evaluation_receipt_hash": coverage_evidence["last_source_evaluation_receipt_hash"],
            "first_checkpoint_hash": coverage_evidence["first_checkpoint_hash"],
            "last_checkpoint_hash": coverage_evidence["last_checkpoint_hash"],
        }
    )
    facts = _facts()
    facts.update(
        {
            "result_available": True,
            "signed_claim_evaluation_verified": True,
            "longitudinal_coverage_evaluation_verified": True,
            "complete_scan_claim_verified": True,
            "time_window_claim_verified": True,
            "bounded_prefix_verified": True,
        }
    )
    axes = [
        {
            "axis": "SOURCE",
            "state": "SIGNED CLAIMS",
            "signal": "VERIFIED_CLAIMS",
            "headline": "Detached occurrence and time claims",
            "detail": f"Assertion {source_evidence['assertion_receipt_hash'][:12]} is bound to checkpoint tree-size {source_evidence['checkpoint_tree_size']}; signatures authenticate claims, not external truth.",
        },
        {
            "axis": "GAP",
            "state": "EXTERNAL TRUST OPEN",
            "signal": "BLOCKED",
            "headline": "Witness authority and index coverage unproven",
            "detail": "Occurrence-index completeness, provider conformance, clock correctness, and future replay absence still require independent evidence.",
        },
        {
            "axis": "MATURITY",
            "state": "BOUNDED PREFIX",
            "signal": "PARTIAL",
            "headline": f"{coverage_evidence['evaluation_count']} consecutive checkpoint claims",
            "detail": f"Registered tree range {coverage_evidence['start_tree_size']} to {coverage_evidence['end_tree_size']}; maximum claimed reference gap {coverage_evidence['maximum_observed_reference_time_gap_ms']} ms.",
        },
        {
            "axis": "PERMISSION",
            "state": "RESEARCH ONLY",
            "signal": "LOCKED",
            "headline": "No admission or trading authority",
            "detail": "The dossier is descriptive only. Current pointer writes, paper authorization, and live orders remain disabled.",
        },
    ]
    return _sealed(
        display_state=POSITIVE_DISPLAY_STATE,
        source_signed_claim_schema=SIGNED_CLAIM_SCHEMA,
        source_signed_claim_fingerprint=SIGNED_CLAIM_STATIC_FINGERPRINT,
        source_coverage_schema=COVERAGE_SCHEMA,
        source_coverage_fingerprint=COVERAGE_STATIC_FINGERPRINT,
        axes=axes,
        summary=summary,
        lineage=lineage,
        facts=facts,
        blockers=list(VERIFIED_BLOCKERS),
    )


def verify_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
    document: Any,
    signed_claim_evaluation_v1: Any,
    signed_claim_evaluation_inputs: Any,
    longitudinal_coverage_evaluation_v1: Any,
    longitudinal_coverage_evaluation_context: Any,
    *,
    expected_signed_claim_evaluation_hash: Any,
    expected_longitudinal_coverage_evaluation_hash: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_strategy_correlation_cross_lag_factor_calibration_long_horizon_provider_identity_uniqueness_freshness_presentation_envelope_v1(
            signed_claim_evaluation_v1,
            signed_claim_evaluation_inputs,
            longitudinal_coverage_evaluation_v1,
            longitudinal_coverage_evaluation_context,
            expected_signed_claim_evaluation_hash=expected_signed_claim_evaluation_hash,
            expected_longitudinal_coverage_evaluation_hash=expected_longitudinal_coverage_evaluation_hash,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return document == expected
